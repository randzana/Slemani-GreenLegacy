"""Citizen endpoints: reports, claim, cleanup, leaderboard, me."""
import json
import random

from flask import Blueprint, current_app, g, jsonify, request

from . import points
from .ai.describe import describe_later, template_description
from .ai.hashing import phash_int
from .ai.scoring import dirtiness as score_dirtiness
from .ai.verify import analyse_cleanup, qr_flags_for
from .auth import error, login_required, public_user
from .db import housekeeping, query
from .storage import path_of, save_upload, url_of
from .strings import INSTRUCTIONS, reason

bp = Blueprint("citizen", __name__)

REPORT_COLUMNS = """r.id, r.reporter_id, r.status, r.dirtiness, r.litter_count, r.litter_classes,
    r.description, r.photo_path, r.created_at, r.cleaned_at,
    ST_Y(r.location::geometry) AS lat, ST_X(r.location::geometry) AS lon"""


def report_json(row):
    out = dict(row)
    out["photo_url"] = url_of(out.pop("photo_path"))
    for key in ("created_at", "cleaned_at"):
        if out.get(key) is not None:
            out[key] = out[key].isoformat()
    return out


def _float(form, key):
    try:
        return float(form[key])
    except (KeyError, ValueError):
        return None


def find_repeat(hashes, own_report_id=None):
    """Return True if any hash is within HASH_MAX_DISTANCE bits of a stored photo or frame.

    For a cleanup, the spot's own photos and earlier attempts are skipped: an honest after-video
    of the same place can look very close to its before photo. Reusing that photo still fails
    later, because the litter is still in it.
    """
    limit = current_app.config["HASH_MAX_DISTANCE"]
    own = own_report_id if own_report_id is not None else -1
    row = query(
        """WITH stored AS (
               SELECT photo_hash AS h FROM reports
                WHERE id <> %(own)s AND (confirms_report_id IS NULL OR confirms_report_id <> %(own)s)
               UNION ALL
               SELECT unnest(frame_hashes) FROM cleanups WHERE report_id <> %(own)s)
           SELECT 1 FROM stored, unnest(%(new)s::bigint[]) AS new(h)
           WHERE bit_count((stored.h # new.h)::bit(64)) <= %(limit)s LIMIT 1""",
        {"own": own, "new": list(hashes), "limit": limit},
        one=True,
    )
    return row is not None


def _hashes_or_none(names):
    """pHash every saved upload. None if one is not a readable image; the files are then removed."""
    try:
        return [phash_int(path_of(n)) for n in names]
    except ValueError:
        for n in names:
            path_of(n).unlink(missing_ok=True)
        return None


# ---------------------------------------------------------------- reports

@bp.post("/reports")
@login_required
def create_report():
    cfg = current_app.config
    lat, lon = _float(request.form, "lat"), _float(request.form, "lon")
    photo = request.files.get("photo")
    if photo is None or lat is None or lon is None:
        return error("missing_fields", 400)

    name = save_upload(photo, "report")
    hashes = _hashes_or_none([name])
    if hashes is None:
        return error("unreadable_image", 400)
    photo_hash = hashes[0]
    if find_repeat([photo_hash]):
        return error("reused_media", 409)

    found = current_app.detector.detect(path_of(name))
    if found.count == 0:
        return error("no_litter", 422)
    level = score_dirtiness(found.count, found.coverage, cfg["LEVEL_COUNT_BANDS"])

    nearby = query(
        f"""SELECT {REPORT_COLUMNS} FROM reports r
            WHERE r.status IN ('open', 'in_progress', 'needs_review')
              AND ST_DWithin(r.location, ST_MakePoint(%s, %s)::geography, %s)
            ORDER BY r.created_at LIMIT 1""",
        (lon, lat, cfg["CONFIRM_RADIUS_M"]),
        one=True,
    )
    common = (g.user["id"], lon, lat, name, photo_hash, found.count, json.dumps(found.classes),
              found.coverage, level)

    if nearby is not None:
        if nearby["reporter_id"] == g.user["id"]:
            return error("already_reported_by_you", 409)
        already = query(
            """SELECT 1 FROM reports WHERE confirms_report_id = %s AND reporter_id = %s""",
            (nearby["id"], g.user["id"]), one=True)
        query(
            """INSERT INTO reports (reporter_id, location, photo_path, photo_hash, litter_count,
                   litter_classes, coverage, dirtiness, status, confirms_report_id)
               VALUES (%s, ST_MakePoint(%s, %s)::geography, %s, %s, %s, %s, %s, %s, 'confirmation', %s)""",
            common + (nearby["id"],),
        )
        earned = 0
        if not already and points.under_daily_cap(g.user["id"]):
            points.award_confirmation(g.user["id"], nearby["id"])
            earned = cfg["CONFIRMATION_POINTS"]
        if not already:
            points.adjust_trust(nearby["reporter_id"], "report_confirmed")
        points.release_report_points(nearby["id"])   # a second person saw it: the first report was real
        return jsonify({"kind": "confirmation", "report": report_json(nearby),
                        "points_pending": earned, "message": reason("confirmed")}), 200

    report = query(
        f"""INSERT INTO reports (reporter_id, location, photo_path, photo_hash, litter_count,
                litter_classes, coverage, dirtiness, description, description_source)
            VALUES (%s, ST_MakePoint(%s, %s)::geography, %s, %s, %s, %s, %s, %s, %s, 'template')
            RETURNING id""",
        common + (template_description(found.classes, found.count, level),), one=True,
    )
    describe_later(current_app._get_current_object(), report["id"], path_of(name), found.classes,
                   found.count, level)
    row = query(f"SELECT {REPORT_COLUMNS} FROM reports r WHERE r.id = %s", (report["id"],), one=True)
    earned, message = 0, None
    if points.under_daily_cap(g.user["id"]):
        earned = points.award_report(g.user["id"], report["id"], level)["amount"]
    else:
        message = reason("daily_cap")
    return jsonify({"kind": "report", "report": report_json(row), "classes": found.classes,
                    "points_pending": earned, "message": message}), 201


@bp.get("/reports")
@login_required
def list_reports():
    housekeeping()
    statuses = request.args.get("status", "open,in_progress,needs_review,clean").split(",")
    sql = f"SELECT {REPORT_COLUMNS} FROM reports r WHERE r.status = ANY(%s)"
    params = [statuses]
    bbox = request.args.get("bbox")                     # minLon,minLat,maxLon,maxLat
    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = (float(v) for v in bbox.split(","))
        except ValueError:
            return error("missing_fields", 400)
        sql += " AND ST_Intersects(r.location::geometry, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
        params += [min_lon, min_lat, max_lon, max_lat]
    sql += " ORDER BY r.created_at DESC LIMIT 500"
    return jsonify([report_json(r) for r in query(sql, params)])


@bp.get("/reports/<int:report_id>")
@login_required
def get_report(report_id):
    housekeeping()
    row = query(f"SELECT {REPORT_COLUMNS} FROM reports r WHERE r.id = %s", (report_id,), one=True)
    if row is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(report_json(row))


# ---------------------------------------------------------------- claim + cleanup

@bp.post("/reports/<int:report_id>/claim")
@login_required
def claim(report_id):
    housekeeping()
    cfg = current_app.config
    report = query("SELECT * FROM reports WHERE id = %s", (report_id,), one=True)
    if report is None or report["status"] not in ("open", "in_progress"):
        return error("not_open", 409)
    if report["reporter_id"] == g.user["id"]:
        recent = query(
            "SELECT now() - created_at < make_interval(hours => %s) AS recent FROM reports WHERE id = %s",
            (cfg["SELF_CLEANUP_BLOCK_HOURS"], report_id), one=True)
        if recent["recent"]:
            return error("self_cleanup_blocked", 403)
    if report["status"] == "in_progress":
        active = query(
            """SELECT 1 FROM challenges WHERE report_id = %s AND user_id <> %s
               AND NOT used AND expires_at > now()""", (report_id, g.user["id"]), one=True)
        if active:
            return error("not_open", 409)

    # one live challenge per person per spot: older unused ones stop working
    query("UPDATE challenges SET used = true WHERE report_id = %s AND user_id = %s AND NOT used",
          (report_id, g.user["id"]))
    code = random.choice(list(INSTRUCTIONS))
    challenge = query(
        """INSERT INTO challenges (user_id, report_id, instruction, instruction_text, expires_at)
           VALUES (%s, %s, %s, %s, now() + make_interval(mins => %s))
           RETURNING id, instruction, instruction_text, expires_at""",
        (g.user["id"], report_id, code, INSTRUCTIONS[code], cfg["CHALLENGE_MINUTES"]),
        one=True,
    )
    query("UPDATE reports SET status = 'in_progress' WHERE id = %s", (report_id,))
    challenge["expires_at"] = challenge["expires_at"].isoformat()
    return jsonify(challenge), 201


def _finish(report, cleanup_fields, verdict, code, status=200):
    """Store the attempt, move the report, award points, and answer the phone."""
    cleanup = query(
        """INSERT INTO cleanups (report_id, cleaner_id, challenge_id, location, frame_paths,
               after_frame_path, frame_hashes, litter_count_before, litter_count_after,
               similarity, verdict, reason_code, reason)
           VALUES (%(report_id)s, %(cleaner_id)s, %(challenge_id)s,
                   CASE WHEN %(lon)s::float8 IS NULL THEN NULL
                        ELSE ST_MakePoint(%(lon)s, %(lat)s)::geography END,
                   %(frame_paths)s, %(after_frame)s, %(frame_hashes)s, %(before)s, %(after)s,
                   %(similarity)s, %(verdict)s, %(code)s, %(reason)s)
           RETURNING id""",
        {**cleanup_fields, "verdict": verdict, "code": code, "reason": reason(code)},
        one=True,
    )
    awarded = {"now": 0, "pending": 0}
    if cleanup_fields["challenge_id"] is not None:
        points.adjust_trust(g.user["id"], code)
    if verdict == "verified":
        query("UPDATE reports SET status = 'clean', cleaned_at = now() WHERE id = %s", (report["id"],))
        awarded = points.award_cleanup(g.user["id"], report["id"], cleanup["id"], report["dirtiness"], True)
        points.release_report_points(report["id"])
    elif verdict == "review":
        query("UPDATE reports SET status = 'needs_review' WHERE id = %s", (report["id"],))
        awarded = points.award_cleanup(g.user["id"], report["id"], cleanup["id"], report["dirtiness"], False)
    elif cleanup_fields["challenge_id"] is not None:
        # only the person holding a valid claim can hand the spot back; a stranger's bad
        # request must not reopen someone else's claim
        query("UPDATE reports SET status = 'open' WHERE id = %s AND status = 'in_progress'", (report["id"],))
    return jsonify({"cleanup_id": cleanup["id"], "verdict": verdict, "reason_code": code,
                    "message": reason(code), "points_now": awarded["now"],
                    "points_pending": awarded["pending"],
                    "litter_before": cleanup_fields["before"],
                    "litter_after": cleanup_fields["after"]}), status


@bp.post("/reports/<int:report_id>/cleanup")
@login_required
def cleanup(report_id):
    cfg = current_app.config
    report = query("SELECT * FROM reports WHERE id = %s", (report_id,), one=True)
    if report is None:
        return jsonify({"error": "not_found"}), 404
    lat, lon = _float(request.form, "lat"), _float(request.form, "lon")
    frames = request.files.getlist("frames")
    try:
        challenge_id = int(request.form.get("challenge_id", ""))
    except ValueError:
        challenge_id = None

    fields = {"report_id": report_id, "cleaner_id": g.user["id"], "challenge_id": None,
              "lat": lat, "lon": lon, "frame_paths": json.dumps([]), "after_frame": None,
              "frame_hashes": [],
              "before": report["litter_count"], "after": None, "similarity": None}

    # 1. challenge: exists, belongs to this user and report, unused, under 5 minutes old
    challenge = query("SELECT *, expires_at <= now() AS expired FROM challenges WHERE id = %s",
                      (challenge_id,), one=True) if challenge_id else None
    if challenge is None or challenge["user_id"] != g.user["id"] or challenge["report_id"] != report_id \
            or challenge["used"]:
        return _finish(report, fields, "rejected", "challenge_invalid", 400)
    fields["challenge_id"] = challenge["id"]
    query("UPDATE challenges SET used = true WHERE id = %s", (challenge["id"],))
    if challenge["expired"]:
        return _finish(report, fields, "rejected", "challenge_expired", 400)

    if len(frames) < cfg["MIN_FRAMES"] or lat is None or lon is None:
        return _finish(report, fields, "rejected", "too_few_frames", 400)
    frames = frames[: cfg["MAX_FRAMES"]]

    # 2. location: the phone is within CLEANUP_RADIUS_M of the report
    near = query(
        "SELECT ST_DWithin(location, ST_MakePoint(%s, %s)::geography, %s) AS ok FROM reports WHERE id = %s",
        (lon, lat, cfg["CLEANUP_RADIUS_M"], report_id), one=True)
    if not near["ok"]:
        return _finish(report, fields, "rejected", "too_far")

    names = [save_upload(f, f"frame{report_id}") for f in frames]
    hashes = _hashes_or_none(names)
    if hashes is None:
        return _finish(report, fields, "rejected", "unreadable_image", 400)
    fields["frame_paths"] = json.dumps(names)

    # 3. repeat check against stored photos and frames of other spots. Only frames of the spot
    #    itself count: the bin's QR sticker looks the same in every honest cleanup at that bin.
    qr_flags = qr_flags_for([path_of(n) for n in names], cfg["QR_PREFIX"])
    scene_hashes = [h for h, is_qr in zip(hashes, qr_flags) if not is_qr]
    if scene_hashes and find_repeat(scene_hashes, own_report_id=report_id):
        return _finish(report, fields, "rejected", "reused_media")
    fields["frame_hashes"] = scene_hashes

    # 4-7. image checks
    result = analyse_cleanup(path_of(report["photo_path"]), report["litter_count"],
                             [path_of(n) for n in names], hashes, challenge["instruction"],
                             current_app.detector, cfg, qr_flags=qr_flags)
    fields["after"], fields["similarity"] = result.litter_after, result.similarity
    if result.best_frame is not None:
        fields["after_frame"] = names[result.best_frame]
    current_app.logger.info("cleanup report=%s verdict=%s details=%s",
                            report_id, result.verdict, result.details)
    return _finish(report, fields, result.verdict, result.reason_code)


# ---------------------------------------------------------------- leaderboard + me

@bp.get("/leaderboard")
@login_required
def leaderboard():
    housekeeping()
    hoods = query(
        """SELECT n.id, n.name, COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'released'
                                                     AND p.kind <> 'redeem'), 0) AS points
           FROM neighbourhoods n
           LEFT JOIN users u ON u.neighbourhood_id = n.id
           LEFT JOIN point_ledger p ON p.user_id = u.id
           GROUP BY n.id ORDER BY points DESC, n.name""")
    people = query(
        """SELECT u.id, u.name, n.name AS neighbourhood,
                  COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'released'
                                           AND p.kind <> 'redeem'), 0) AS points
           FROM users u LEFT JOIN neighbourhoods n ON n.id = u.neighbourhood_id
           LEFT JOIN point_ledger p ON p.user_id = u.id
           WHERE u.role = 'citizen'
           GROUP BY u.id, n.name ORDER BY points DESC, u.name LIMIT 10""")
    return jsonify({"neighbourhoods": hoods, "citizens": people})


@bp.get("/me")
@login_required
def me():
    housekeeping()
    hood = query("SELECT name FROM neighbourhoods WHERE id = %s", (g.user["neighbourhood_id"],), one=True)
    history = query(
        """SELECT amount, kind, status, report_id, detail, release_at, created_at
           FROM point_ledger WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT 30""",
        (g.user["id"],))
    for h in history:
        for key in ("release_at", "created_at"):
            if h[key] is not None:
                h[key] = h[key].isoformat()
    return jsonify({**public_user(g.user), "neighbourhood": hood["name"] if hood else None,
                    "trust_level": g.user["trust_level"],
                    **points.ranks(g.user["id"], g.user["neighbourhood_id"]),
                    **points.balance(g.user["id"]), "history": history})
