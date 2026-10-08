"""Municipality endpoints (staff only) and the dashboard page."""
import json

from flask import Blueprint, g, jsonify, render_template, request

from . import points
from .db import housekeeping, query
from .auth import staff_required
from .routes import REPORT_COLUMNS, report_json
from .storage import url_of
from .strings import reason

bp = Blueprint("admin", __name__)


@bp.get("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@bp.get("/admin/reports")
@staff_required
def priority_list():
    housekeeping()
    rows = query(
        f"""SELECT {REPORT_COLUMNS},
                   EXTRACT(EPOCH FROM now() - r.created_at) / 3600 AS age_hours,
                   (SELECT count(*) FROM reports c WHERE c.confirms_report_id = r.id) AS confirmations
            FROM reports r
            WHERE r.status IN ('open', 'in_progress', 'needs_review')
            ORDER BY r.dirtiness DESC, r.created_at ASC""")
    out = []
    for r in rows:
        item = report_json(r)
        item["age_hours"] = round(float(item["age_hours"]), 1)
        out.append(item)
    return jsonify(out)


def _cleanup_rows(where, params=()):
    rows = query(
        f"""SELECT c.id, c.report_id, c.verdict, c.reason_code, c.reason, c.litter_count_before,
                   c.litter_count_after, c.similarity, c.frame_paths, c.after_frame_path,
                   c.created_at, c.reviewed_at,
                   r.photo_path AS before_photo, r.dirtiness, u.name AS cleaner
            FROM cleanups c JOIN reports r ON r.id = c.report_id JOIN users u ON u.id = c.cleaner_id
            WHERE {where} ORDER BY c.created_at DESC LIMIT 200""", params)
    out = []
    for r in rows:
        frames = r.pop("frame_paths") or []
        if isinstance(frames, str):
            frames = json.loads(frames)
        r["before_url"] = url_of(r.pop("before_photo"))
        r["frame_urls"] = [url_of(f) for f in frames]
        best = r.pop("after_frame_path")
        r["after_url"] = url_of(best) if best else (r["frame_urls"][-1] if r["frame_urls"] else None)
        for key in ("created_at", "reviewed_at"):
            if r[key] is not None:
                r[key] = r[key].isoformat()
        out.append(r)
    return out


@bp.get("/admin/cleanups")
@staff_required
def cleanup_log():
    verdict = request.args.get("verdict")
    if verdict:
        return jsonify(_cleanup_rows("c.verdict = %s", (verdict,)))
    return jsonify(_cleanup_rows("true"))


@bp.post("/admin/cleanups/<int:cleanup_id>/review")
@staff_required
def review(cleanup_id):
    decision = (request.get_json(silent=True) or {}).get("decision")
    cleanup = query("SELECT * FROM cleanups WHERE id = %s", (cleanup_id,), one=True)
    if cleanup is None or cleanup["verdict"] != "review" or cleanup["reviewed_at"] is not None:
        return jsonify({"error": "not_reviewable"}), 409
    if decision == "approve":
        query("""UPDATE cleanups SET verdict = 'verified', reason_code = 'approved_by_staff',
                 reason = %s, reviewed_by = %s, reviewed_at = now() WHERE id = %s""",
              (reason("approved_by_staff"), g.user["id"], cleanup_id))
        query("UPDATE reports SET status = 'clean', cleaned_at = now() WHERE id = %s",
              (cleanup["report_id"],))
        points.approve_reviewed_cleanup(cleanup_id)
        points.release_report_points(cleanup["report_id"])
    elif decision == "reject":
        query("""UPDATE cleanups SET verdict = 'rejected', reason_code = 'rejected_by_staff',
                 reason = %s, reviewed_by = %s, reviewed_at = now() WHERE id = %s""",
              (reason("rejected_by_staff"), g.user["id"], cleanup_id))
        query("UPDATE reports SET status = 'open' WHERE id = %s", (cleanup["report_id"],))
        points.revoke_cleanup(cleanup_id)
    else:
        return jsonify({"error": "bad_decision"}), 400
    return jsonify({"ok": True, "decision": decision})


@bp.get("/admin/stats")
@staff_required
def stats():
    housekeeping()
    return jsonify(query(
        """SELECT
             (SELECT count(*) FROM reports WHERE status <> 'confirmation') AS reported,
             (SELECT count(*) FROM reports WHERE status IN ('open', 'in_progress')) AS open,
             (SELECT count(*) FROM reports WHERE status = 'needs_review') AS needs_review,
             (SELECT count(*) FROM reports WHERE status = 'clean') AS cleaned,
             (SELECT COALESCE(SUM(GREATEST(litter_count_before - COALESCE(litter_count_after, 0), 0)), 0)
                FROM cleanups WHERE verdict = 'verified') AS litter_removed,
             (SELECT count(*) FROM users WHERE role = 'citizen') AS citizens""",
        one=True))
