"""The demo loop through the real API and a real PostGIS database:
report -> map -> claim -> after-video -> verify -> points, plus every rejection path."""
import psycopg

from app.config import Config
from conftest import SLEMANI, TEST_DB
from tools import synthetic

NEAR = (SLEMANI[0] + 0.0001, SLEMANI[1])          # about 11 m away
FAR = (SLEMANI[0] + 0.01, SLEMANI[1])             # about 1.1 km away


def dirty_spot(api, seed=10, litter=6, at=SLEMANI):
    """A citizen reports a littered spot. Returns (reporter headers, report json, clean scene)."""
    reporter = api.signup("ڕاپۆرتکەر")
    scene = synthetic.place(seed)
    r = api.report(reporter, synthetic.with_litter(scene, litter, seed), *at)
    assert r.status_code == 201, r.json
    return reporter, r.json["report"], scene


def claimed(api, report_id):
    cleaner = api.signup("پاککەرەوە")
    c = api.claim(cleaner, report_id)
    assert c.status_code == 201, c.json
    return cleaner, c.json


def test_signup_login_and_duplicate_phone(client):
    r = client.post("/auth/signup", json={"name": "ڕەند", "phone": "07701234567", "password": "secret123"})
    assert r.status_code == 201
    assert client.post("/auth/signup", json={"name": "x", "phone": "07701234567",
                                             "password": "secret123"}).status_code == 409
    assert client.post("/auth/login", json={"phone": "07701234567", "password": "wrong!!"}).status_code == 401
    ok = client.post("/auth/login", json={"phone": "07701234567", "password": "secret123"})
    assert ok.status_code == 200 and ok.json["token"]
    assert client.get("/me").status_code == 401


def test_report_scores_dirtiness_and_holds_points(api):
    reporter, report, _ = dirty_spot(api, litter=8)
    assert report["status"] == "open"
    assert report["dirtiness"] == 3 and report["litter_count"] >= 7
    me = api.me(reporter)
    assert me["pending"] > 0 and me["released"] == 0          # pending until confirmed or cleaned


def test_clean_photo_is_refused(api):
    citizen = api.signup()
    r = api.report(citizen, synthetic.place(11))
    assert r.status_code == 422 and r.json["error"] == "no_litter"


def test_same_photo_twice_is_refused(api):
    citizen = api.signup()
    image = synthetic.with_litter(synthetic.place(12), 4)
    assert api.report(citizen, image).status_code == 201
    other = api.signup()
    r = api.report(other, image, *FAR)
    assert r.status_code == 409 and r.json["error"] == "reused_media"


def test_second_report_nearby_is_a_confirmation(api):
    reporter, report, scene = dirty_spot(api, seed=13)
    confirmer = api.signup()
    r = api.report(confirmer, synthetic.view(synthetic.with_litter(scene, 6, 99), 3), *NEAR)
    assert r.status_code == 200 and r.json["kind"] == "confirmation"
    assert r.json["report"]["id"] == report["id"]
    assert api.me(reporter)["released"] > 0                   # the first reporter's points are freed
    again = api.report(reporter, synthetic.with_litter(synthetic.place(77), 3), *NEAR)
    assert again.status_code == 409 and again.json["error"] == "already_reported_by_you"


def test_reporter_cannot_clean_own_spot_within_24h(api):
    reporter, report, _ = dirty_spot(api, seed=14)
    r = api.claim(reporter, report["id"])
    assert r.status_code == 403 and r.json["error"] == "self_cleanup_blocked"


def test_full_loop_verified(api, client):
    reporter, report, scene = dirty_spot(api, seed=15, litter=6)
    cleaner, challenge = claimed(api, report["id"])
    assert challenge["instruction"] in ("qr_first", "qr_last") and challenge["instruction_text"]
    spot = client.get(f"/reports/{report['id']}", headers=cleaner).json
    assert spot["status"] == "in_progress"

    frames = synthetic.cleanup_frames(scene, challenge["instruction"])
    r = api.cleanup(cleaner, report["id"], challenge["id"], frames, *NEAR)
    assert r.status_code == 200, r.json
    assert r.json["verdict"] == "verified", r.json
    assert r.json["litter_after"] == 0
    total = Config.CLEANUP_POINTS[report["dirtiness"]]
    now_part = round(total * Config.IMMEDIATE_SHARE)
    assert r.json["points_now"] == now_part and r.json["points_pending"] == total - now_part

    assert client.get(f"/reports/{report['id']}", headers=cleaner).json["status"] == "clean"
    me = api.me(cleaner)
    assert me["released"] == now_part and me["pending"] == total - now_part
    assert api.me(reporter)["released"] > 0

    # the 24-hour hold ends
    with psycopg.connect(TEST_DB) as conn:
        conn.execute("UPDATE point_ledger SET release_at = now() - interval '1 minute' WHERE release_at IS NOT NULL")
    assert api.me(cleaner)["released"] == total

    board = client.get("/leaderboard", headers=cleaner).json
    assert board["citizens"][0]["points"] >= total
    assert board["neighbourhoods"][0]["points"] > 0

    # the same video cannot be used for another spot
    _r2, report2, _s2 = dirty_spot(api, seed=16, at=FAR)
    cleaner2, challenge2 = claimed(api, report2["id"])
    r = api.cleanup(cleaner2, report2["id"], challenge2["id"], frames, *FAR)
    assert r.json["verdict"] == "rejected" and r.json["reason_code"] == "reused_media"
    assert client.get(f"/reports/{report2['id']}", headers=cleaner2).json["status"] == "open"


def test_two_cleanups_at_the_same_bin_are_both_fine(api):
    """Both videos film the same QR sticker; that alone must not count as reused media."""
    _r1, report1, scene1 = dirty_spot(api, seed=40)
    cleaner, challenge = claimed(api, report1["id"])
    r = api.cleanup(cleaner, report1["id"], challenge["id"],
                    synthetic.cleanup_frames(scene1, challenge["instruction"]))
    assert r.json["verdict"] == "verified", r.json

    _r2, report2, scene2 = dirty_spot(api, seed=41, at=FAR)
    challenge2 = api.claim(cleaner, report2["id"]).json
    r = api.cleanup(cleaner, report2["id"], challenge2["id"],
                    synthetic.cleanup_frames(scene2, challenge2["instruction"]), *FAR)
    assert r.json["verdict"] == "verified", r.json


def test_wrong_instruction_order_is_rejected(api):
    _rep, report, scene = dirty_spot(api, seed=17)
    cleaner, challenge = claimed(api, report["id"])
    wrong = "qr_last" if challenge["instruction"] == "qr_first" else "qr_first"
    r = api.cleanup(cleaner, report["id"], challenge["id"], synthetic.cleanup_frames(scene, wrong))
    assert r.json["verdict"] == "rejected" and r.json["reason_code"] == "instruction_not_followed"
    # a challenge works once
    r = api.cleanup(cleaner, report["id"], challenge["id"],
                    synthetic.cleanup_frames(scene, challenge["instruction"]))
    assert r.json["reason_code"] == "challenge_invalid"


def test_too_far_and_static_and_expired(api):
    _rep, report, scene = dirty_spot(api, seed=18)
    cleaner, challenge = claimed(api, report["id"])
    frames = synthetic.cleanup_frames(scene, challenge["instruction"])
    r = api.cleanup(cleaner, report["id"], challenge["id"], frames, *FAR)
    assert r.json["reason_code"] == "too_far"

    challenge = api.claim(cleaner, report["id"]).json
    still = [synthetic.view(scene, 1)] * 6
    r = api.cleanup(cleaner, report["id"], challenge["id"], still)
    assert r.json["reason_code"] == "static_frames"

    challenge = api.claim(cleaner, report["id"]).json
    with psycopg.connect(TEST_DB) as conn:
        conn.execute("UPDATE challenges SET expires_at = now() - interval '1 second' WHERE id = %s",
                     (challenge["id"],))
    r = api.cleanup(cleaner, report["id"], challenge["id"], frames)
    assert r.json["reason_code"] == "challenge_expired"


def test_litter_still_there_is_rejected(api):
    _rep, report, scene = dirty_spot(api, seed=19, litter=6)
    cleaner, challenge = claimed(api, report["id"])
    dirty = synthetic.with_litter(scene, 6, 19)
    r = api.cleanup(cleaner, report["id"], challenge["id"], synthetic.cleanup_frames(dirty, challenge["instruction"]))
    assert r.json["verdict"] == "rejected" and r.json["reason_code"] == "litter_still_there"


def test_other_place_goes_to_review_and_staff_decides(api, client):
    _rep, report, _scene = dirty_spot(api, seed=20)
    cleaner, challenge = claimed(api, report["id"])
    elsewhere = synthetic.place(21)
    r = api.cleanup(cleaner, report["id"], challenge["id"],
                    synthetic.cleanup_frames(elsewhere, challenge["instruction"]))
    assert r.json["verdict"] == "review" and r.json["reason_code"] == "same_place_unsure"
    assert api.me(cleaner)["released"] == 0

    citizen_try = client.get("/admin/cleanups?verdict=review", headers=cleaner)
    assert citizen_try.status_code == 403
    staff = api.staff()
    queue = client.get("/admin/cleanups?verdict=review", headers=staff).json
    assert [c["id"] for c in queue] == [r.json["cleanup_id"]]
    assert queue[0]["before_url"].startswith("/files/") and queue[0]["after_url"]

    ok = client.post(f"/admin/cleanups/{r.json['cleanup_id']}/review", json={"decision": "approve"},
                     headers=staff)
    assert ok.status_code == 200
    assert api.me(cleaner)["released"] > 0
    assert client.get(f"/reports/{report['id']}", headers=cleaner).json["status"] == "clean"
    again = client.post(f"/admin/cleanups/{r.json['cleanup_id']}/review", json={"decision": "reject"},
                        headers=staff)
    assert again.status_code == 409


def test_staff_reject_revokes_points(api, client):
    _rep, report, _scene = dirty_spot(api, seed=22)
    cleaner, challenge = claimed(api, report["id"])
    r = api.cleanup(cleaner, report["id"], challenge["id"],
                    synthetic.cleanup_frames(synthetic.place(23), challenge["instruction"]))
    staff = api.staff()
    client.post(f"/admin/cleanups/{r.json['cleanup_id']}/review", json={"decision": "reject"}, headers=staff)
    me = api.me(cleaner)
    assert me["released"] == 0 and me["pending"] == 0
    assert client.get(f"/reports/{report['id']}", headers=cleaner).json["status"] == "open"


def test_dashboard_endpoints(api, client):
    dirty_spot(api, seed=24, litter=2)
    dirty_spot(api, seed=25, litter=25, at=FAR)
    staff = api.staff()
    ranked = client.get("/admin/reports", headers=staff).json
    assert [r["dirtiness"] for r in ranked] == sorted([r["dirtiness"] for r in ranked], reverse=True)
    stats = client.get("/admin/stats", headers=staff).json
    assert stats["reported"] == 2 and stats["open"] == 2 and stats["cleaned"] == 0
    box = f"{SLEMANI[1] - 0.001},{SLEMANI[0] - 0.001},{SLEMANI[1] + 0.001},{SLEMANI[0] + 0.001}"
    assert len(client.get(f"/reports?bbox={box}", headers=staff).json) == 1
    assert client.get("/dashboard").status_code == 200


def test_daily_cap_on_rewarded_reports(api, app):
    app.config["DAILY_REWARDED_REPORTS"] = 2
    citizen = api.signup()
    results = []
    for i in range(3):
        r = api.report(citizen, synthetic.with_litter(synthetic.place(30 + i), 3), SLEMANI[0] + 0.01 * i, SLEMANI[1])
        results.append(r.json["points_pending"])
    assert results[0] > 0 and results[1] > 0 and results[2] == 0
