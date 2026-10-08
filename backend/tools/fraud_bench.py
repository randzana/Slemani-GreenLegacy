"""Fraud bench: cleanup attempts, honest ones and tricks, through the real API and verification chain.
Prints a markdown table for the slides.

    python tools/fraud_bench.py                     # 20 synthetic attempts on the TEST database (wiped)
    python tools/fraud_bench.py --from-db           # real attempts on the live server (read-only)
    python tools/fraud_bench.py --from-db --rerun   # ...and what the chain says now with today's settings

Synthetic mode uses red rectangles as litter (ColorBlobDetector), like the automated tests. For the
"20 fake videos" on day two, make the attempts with the real app against the real server, then run
--from-db to get the table; --rerun shows the effect of a changed setting (e.g. SAME_PLACE_MIN_INLIERS)
on the same stored frames without filming again. --rerun repeats the image checks (steps 4-8) only:
an attempt rejected as reused media (step 3, the repeat check) is shown as not re-run.

To try --rerun on the synthetic attempts, keep their files: --uploads DIR, then --from-db --rerun with
DATABASE_URL=<the test database> UPLOAD_DIR=DIR DETECTOR_KIND=colorblob.
"""
import argparse
import io
import json
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.config import Config  # noqa: E402
from tools import synthetic  # noqa: E402

TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql://gl:gl@localhost:5432/greenlegacy_test")
BASE = (35.50, 45.43)


class Bench:
    """Drives the API like the phone does, one fresh spot per attempt (each about 1 km apart)."""

    def __init__(self, client, database_url):
        self.client = client
        self.database_url = database_url
        self.phone = 7800000000
        self.spots = 0
        self.honest_frames = None

    def user(self, name="هاوڵاتی"):
        self.phone += 1
        r = self.client.post("/auth/signup", json={"name": name, "phone": f"0{self.phone}",
                                                   "password": "secret123", "neighbourhood_id": 1})
        return {"Authorization": f"Bearer {r.json['token']}"}

    def spot(self, litter=6):
        self.spots += 1
        seed = 500 + self.spots
        at = (BASE[0] + 0.01 * self.spots, BASE[1])
        scene = synthetic.place(seed)
        reporter = self.user("ڕاپۆرتکەر")
        before = synthetic.with_litter(scene, litter, seed)
        r = self.client.post("/reports", headers=reporter, content_type="multipart/form-data",
                             data={"lat": str(at[0]), "lon": str(at[1]),
                                   "photo": (io.BytesIO(synthetic.encode(before)), "photo.jpg")})
        assert r.status_code == 201, r.json
        return {"id": r.json["report"]["id"], "scene": scene, "before": before, "at": at,
                "reporter": reporter, "litter": litter, "seed": seed}

    def claim(self, headers, spot):
        return self.client.post(f"/reports/{spot['id']}/claim", headers=headers)

    def cleanup(self, headers, spot, challenge_id, frames, at=None):
        at = at or spot["at"]
        data = {"lat": str(at[0]), "lon": str(at[1]), "challenge_id": str(challenge_id),
                "frames": [(io.BytesIO(synthetic.encode(f)), f"f{i}.jpg") for i, f in enumerate(frames)]}
        start = time.perf_counter()
        r = self.client.post(f"/reports/{spot['id']}/cleanup", headers=headers, data=data,
                             content_type="multipart/form-data")
        return r.json["verdict"], r.json["reason_code"], (time.perf_counter() - start) * 1000

    def claimed(self, spot):
        cleaner = self.user("پاککەرەوە")
        ch = self.claim(cleaner, spot).json
        return cleaner, ch

    @staticmethod
    def wrong(instruction):
        return "qr_last" if instruction == "qr_first" else "qr_first"

    # ---- honest attempts
    def honest(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        frames = synthetic.cleanup_frames(spot["scene"], ch["instruction"])
        self.honest_frames = self.honest_frames or frames
        return self.cleanup(cleaner, spot, ch["id"], frames)

    def same_bin_again(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        return self.cleanup(cleaner, spot, ch["id"], synthetic.cleanup_frames(spot["scene"], ch["instruction"],
                                                                              qr_text="GL-BIN-001"))

    def shortest_video(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        return self.cleanup(cleaner, spot, ch["id"],
                            synthetic.cleanup_frames(spot["scene"], ch["instruction"], count=Config.MIN_FRAMES))

    # ---- tricks
    def reused_video(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        return self.cleanup(cleaner, spot, ch["id"], self.honest_frames)

    def reordered_copy(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        return self.cleanup(cleaner, spot, ch["id"], list(reversed(self.honest_frames)))

    def still_photo(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        return self.cleanup(cleaner, spot, ch["id"], [synthetic.view(spot["scene"], 1)] * 8)

    def qr_wrong_time(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        return self.cleanup(cleaner, spot, ch["id"],
                            synthetic.cleanup_frames(spot["scene"], self.wrong(ch["instruction"])))

    def no_qr(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        return self.cleanup(cleaner, spot, ch["id"], [synthetic.view(spot["scene"], i + 1) for i in range(8)])

    def far_away(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        far = (spot["at"][0], spot["at"][1] + 0.012)                # about 1 km east
        return self.cleanup(cleaner, spot, ch["id"],
                            synthetic.cleanup_frames(spot["scene"], ch["instruction"]), at=far)

    def expired(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        with psycopg.connect(self.database_url) as conn:
            conn.execute("UPDATE challenges SET expires_at = now() - interval '1 second' WHERE id = %s",
                         (ch["id"],))
        return self.cleanup(cleaner, spot, ch["id"], synthetic.cleanup_frames(spot["scene"], ch["instruction"]))

    def challenge_twice(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        self.cleanup(cleaner, spot, ch["id"], synthetic.cleanup_frames(spot["scene"], self.wrong(ch["instruction"])))
        return self.cleanup(cleaner, spot, ch["id"], synthetic.cleanup_frames(spot["scene"], ch["instruction"]))

    def someone_elses_challenge(self):
        spot = self.spot()
        _owner, ch = self.claimed(spot)
        thief = self.user("دز")
        return self.cleanup(thief, spot, ch["id"], synthetic.cleanup_frames(spot["scene"], ch["instruction"]))

    def other_place(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        return self.cleanup(cleaner, spot, ch["id"],
                            synthetic.cleanup_frames(synthetic.place(spot["seed"] + 9000), ch["instruction"]))

    def litter_still_there(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        dirty = synthetic.with_litter(spot["scene"], spot["litter"], spot["seed"])
        return self.cleanup(cleaner, spot, ch["id"], synthetic.cleanup_frames(dirty, ch["instruction"]))

    def half_left(self):
        spot = self.spot(litter=6)
        cleaner, ch = self.claimed(spot)
        partly = synthetic.with_litter(spot["scene"], 2, spot["seed"])    # 2 of the same 6 items remain
        return self.cleanup(cleaner, spot, ch["id"], synthetic.cleanup_frames(partly, ch["instruction"]))

    def before_photo_as_after(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        return self.cleanup(cleaner, spot, ch["id"], synthetic.cleanup_frames(spot["before"], ch["instruction"]))

    def too_short(self):
        spot = self.spot()
        cleaner, ch = self.claimed(spot)
        frames = synthetic.cleanup_frames(spot["scene"], ch["instruction"])[: Config.MIN_FRAMES - 1]
        return self.cleanup(cleaner, spot, ch["id"], frames)

    def own_spot(self):
        spot = self.spot()
        r = self.claim(spot["reporter"], spot)
        return "rejected", r.json["error"], 0.0

    def already_taken(self):
        spot = self.spot()
        self.claimed(spot)
        r = self.claim(self.user(), spot)
        return "rejected", r.json["error"], 0.0


SCENARIOS = [
    # (what happens, expected verdict, expected reason, method)
    ("honest cleanup", "verified", "verified", "honest"),
    ("honest cleanup, another spot", "verified", "verified", "honest"),
    ("honest, same bin sticker as an earlier cleanup", "verified", "verified", "same_bin_again"),
    ("honest, shortest allowed video", "verified", "verified", "shortest_video"),
    ("old video re-sent for another spot", "rejected", "reused_media", "reused_video"),
    ("old video re-sent backwards", "rejected", "reused_media", "reordered_copy"),
    ("one still photo instead of a video", "rejected", "static_frames", "still_photo"),
    ("QR sticker shown at the wrong time", "rejected", "instruction_not_followed", "qr_wrong_time"),
    ("no QR sticker filmed", "rejected", "instruction_not_followed", "no_qr"),
    ("filmed 1 km from the spot", "rejected", "too_far", "far_away"),
    ("challenge older than 5 minutes", "rejected", "challenge_expired", "expired"),
    ("same challenge used twice", "rejected", "challenge_invalid", "challenge_twice"),
    ("someone else's challenge", "rejected", "challenge_invalid", "someone_elses_challenge"),
    ("video of a different place", "review", "same_place_unsure", "other_place"),
    ("litter still there", "rejected", "litter_still_there", "litter_still_there"),
    ("a third of the litter left", "review", "litter_partly_remaining", "half_left"),
    ("the before photo sent as the after video", "rejected", "litter_still_there", "before_photo_as_after"),
    ("video too short", "rejected", "too_few_frames", "too_short"),
    ("reporter cleans their own spot at once", "rejected", "self_cleanup_blocked", "own_spot"),
    ("claim a spot someone is already cleaning", "rejected", "not_open", "already_taken"),
]


def synthetic_bench(database_url, force, uploads=None):
    from app import create_app
    from app.ai.detector import ColorBlobDetector
    from app.strings import reason
    from seed import seed

    if "test" not in database_url.rsplit("/", 1)[-1] and not force:
        raise SystemExit(f"refusing to wipe {database_url}: it does not look like a test database "
                         "(set TEST_DATABASE_URL, or pass --force)")
    seed(database_url)
    with tempfile.TemporaryDirectory() as temporary:
        app = create_app({"DATABASE_URL": database_url, "UPLOAD_DIR": uploads or temporary, "TESTING": True,
                          "DESCRIBE_WITH_CLAUDE": False}, detector=ColorBlobDetector())
        bench = Bench(app.test_client(), database_url)
        rows = []
        for i, (label, verdict, code, method) in enumerate(SCENARIOS, start=1):
            got_verdict, got_code, ms = getattr(bench, method)()
            ok = (got_verdict, got_code) == (verdict, code)
            rows.append((i, label, verdict, got_verdict, got_code, reason(got_code), ok, ms, verdict == "verified"))

    print("\n| # | attempt | expected | result | reason | ✓ | ms |")
    print("|---|---|---|---|---|---|---|")
    for i, label, verdict, got, code, message, ok, ms, _ in rows:
        timing = f"{ms:.0f}" if ms else "—"                 # claim refusals never reach the chain
        print(f"| {i} | {label} | {verdict} | {got} | {code} — {message} | {'✓' if ok else '✗'} | {timing} |")
    honest = [r for r in rows if r[8]]
    tricks = [r for r in rows if not r[8]]
    timed = sorted(r[7] for r in rows if r[7])
    print(f"\nHonest cleanups verified: {sum(r[3] == 'verified' for r in honest)}/{len(honest)}")
    print(f"Tricks paid automatically: {sum(r[3] == 'verified' for r in tricks)}/{len(tricks)} "
          f"(rejected {sum(r[3] == 'rejected' for r in tricks)}, sent to staff review "
          f"{sum(r[3] == 'review' for r in tricks)})")
    print(f"Matched the expected result: {sum(r[6] for r in rows)}/{len(rows)}")
    if timed:
        print(f"Verification time per attempt: median {timed[len(timed) // 2]:.0f} ms "
              f"(colour detector; YOLOv8 on a laptop CPU adds ~0.13 s per counted frame)")
    return all(r[6] for r in rows)


def from_db(database_url, hours, rerun):
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            """SELECT c.id, c.created_at, c.verdict, c.reason_code, c.reason, c.litter_count_before,
                      c.litter_count_after, c.similarity, c.frame_paths, u.name AS cleaner,
                      r.photo_path, r.litter_count, ch.instruction
               FROM cleanups c JOIN users u ON u.id = c.cleaner_id JOIN reports r ON r.id = c.report_id
               LEFT JOIN challenges ch ON ch.id = c.challenge_id
               WHERE c.created_at > now() - make_interval(hours => %s) ORDER BY c.id""",
            (hours,)).fetchall()
    if not rows:
        print(f"no cleanup attempts in the last {hours} hours")
        return True

    if rerun:
        from app.ai.detector import make_detector
        from app.ai.hashing import phash_int
        from app.ai.verify import analyse_cleanup, qr_flags_for
        cfg = {k: getattr(Config, k) for k in dir(Config) if k.isupper()}
        detector = make_detector(cfg)
        uploads = Path(cfg["UPLOAD_DIR"])

    print(f"\n| # | when | cleaner | verdict | reason | litter before → after | ORB inliers |"
          + (" now |" if rerun else ""))
    print("|---|---|---|---|---|---|---|" + ("---|" if rerun else ""))
    changed = not_rerun = 0
    for r in rows:
        frames = r["frame_paths"] if isinstance(r["frame_paths"], list) else json.loads(r["frame_paths"] or "[]")
        after = "—" if r["litter_count_after"] is None else r["litter_count_after"]
        inliers = "—" if r["similarity"] is None else f"{r['similarity']:.0f}"
        line = (f"| {r['id']} | {r['created_at']:%H:%M} | {r['cleaner']} | {r['verdict']} | "
                f"{r['reason_code']} — {r['reason']} | {r['litter_count_before']} → {after} | {inliers} |")
        if rerun:
            now = "—"
            paths = [uploads / f for f in frames]
            if r["reason_code"] == "reused_media":
                # stopped by the repeat check against everything stored before it (step 3), before any
                # image check: running steps 4-8 on its frames would invent a verdict it never had
                now = "not re-run (repeat check)"
                not_rerun += 1
            elif not all(p.exists() for p in paths + [uploads / r["photo_path"]]):
                now = "files missing (check UPLOAD_DIR)"
            elif len(frames) >= cfg["MIN_FRAMES"] and r["instruction"]:
                result = analyse_cleanup(uploads / r["photo_path"], r["litter_count"], paths,
                                         [phash_int(p) for p in paths], r["instruction"], detector, cfg,
                                         qr_flags=qr_flags_for(paths, cfg["QR_PREFIX"]))
                verdict, code = result.verdict, result.reason_code
                if r["reason_code"] == "similar_to_earlier" and verdict == "verified":
                    # the rule of routes.cleanup: frames like an earlier cleanup of the same corner go to a person
                    verdict, code = "review", "similar_to_earlier"
                now = f"{verdict} ({code})"
                changed += verdict != r["verdict"] and r["reason_code"] not in (
                    "approved_by_staff", "rejected_by_staff")
            line += f" {now} |"
        print(line)
    by_verdict = Counter(r["verdict"] for r in rows)
    by_reason = Counter(r["reason_code"] for r in rows)
    print(f"\n{len(rows)} attempts: " + ", ".join(f"{v} {n}" for v, n in by_verdict.most_common()))
    print("reasons: " + ", ".join(f"{c} {n}" for c, n in by_reason.most_common()))
    if rerun:
        print(f"verdicts that change with today's settings: {changed}"
              + (f" (not re-run: {not_rerun} rejected by the repeat check)" if not_rerun else ""))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-db", action="store_true", help="report real attempts from DATABASE_URL")
    parser.add_argument("--hours", type=int, default=48, help="with --from-db: how far back")
    parser.add_argument("--rerun", action="store_true", help="with --from-db: run the image checks again")
    parser.add_argument("--force", action="store_true", help="allow wiping a database without 'test' in its name")
    parser.add_argument("--uploads", help="synthetic mode: keep the photos and frames in this folder "
                                          "(default: a temporary one, deleted afterwards)")
    args = parser.parse_args()
    if args.from_db:
        ok = from_db(Config.DATABASE_URL, args.hours, args.rerun)
    else:
        ok = synthetic_bench(TEST_DB, args.force, args.uploads)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
