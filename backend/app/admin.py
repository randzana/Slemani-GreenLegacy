"""Municipality endpoints (staff only) and the dashboard page."""
import datetime as dt
import json
import re

from flask import Blueprint, current_app, g, jsonify, render_template, request

from . import accounts, points
from .db import housekeeping, query
from .auth import error, json_body, staff_required
from .routes import REPORT_COLUMNS, report_json
from .storage import url_of
from .strings import CATEGORY_NAMES, REWARDS, reason
from .bins import BIN_COLUMNS, bin_json, generate_sticker_png

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
                   r.photo_path AS before_photo, r.dirtiness, r.description,
                   u.name AS cleaner, u.trust_level AS cleaner_trust
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
        return error("not_reviewable", 409)
    if decision == "approve":
        query("""UPDATE cleanups SET verdict = 'verified', reason_code = 'approved_by_staff',
                 reason = %s, reviewed_by = %s, reviewed_at = now() WHERE id = %s""",
              (reason("approved_by_staff"), g.user["id"], cleanup_id))
        query("UPDATE reports SET status = 'clean', cleaned_at = now() WHERE id = %s",
              (cleanup["report_id"],))
        points.approve_reviewed_cleanup(cleanup_id)
        points.release_report_points(cleanup["report_id"])
        points.adjust_trust(cleanup["cleaner_id"], "approved_by_staff")
    elif decision == "reject":
        query("""UPDATE cleanups SET verdict = 'rejected', reason_code = 'rejected_by_staff',
                 reason = %s, reviewed_by = %s, reviewed_at = now() WHERE id = %s""",
              (reason("rejected_by_staff"), g.user["id"], cleanup_id))
        query("UPDATE reports SET status = 'open' WHERE id = %s", (cleanup["report_id"],))
        points.revoke_cleanup(cleanup_id)
        points.adjust_trust(cleanup["cleaner_id"], "rejected_by_staff")
    else:
        return error("bad_decision", 400)
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
             (SELECT count(*) FROM users WHERE role = 'citizen') AS citizens,
             (SELECT count(*) FROM places WHERE kind = 'household' AND verification_status = 'verified') AS households,
             (SELECT count(*) FROM places WHERE kind = 'business' AND verification_status = 'verified') AS businesses,
             (SELECT count(*) FROM places WHERE verification_status = 'pending') AS pending_places,
             (SELECT count(*) FROM trash_bins) AS bins_total,
             (SELECT count(*) FROM trash_bins WHERE status = 'full') AS bins_full,
             (SELECT count(*) FROM pins WHERE status = 'active') AS pins_active,
             (SELECT count(*) FROM point_ledger WHERE kind = 'redeem' AND honoured_at IS NULL) AS vouchers_waiting""",
        one=True))


@bp.get("/admin/neighbourhoods")
@staff_required
def neighbourhood_league():
    """The league and the map's areas: points by where people live (the /leaderboard rule), spots by
    where they are. Spots count only inside a loaded boundary (tools/import_boundaries.py), so a
    neighbourhood without one shows 0; 'open' means open or in_progress, as in /admin/stats."""
    housekeeping()
    return jsonify(query(
        """SELECT n.id, n.name, ST_AsGeoJSON(n.boundary, 6)::json AS boundary,
                  (SELECT count(*) FROM users u
                   WHERE u.neighbourhood_id = n.id AND u.role = 'citizen') AS citizens,
                  -- homes are counted, never drawn: their locations stay off the dashboard map
                  (SELECT count(*) FROM places pl WHERE pl.neighbourhood_id = n.id AND pl.kind = 'household'
                     AND pl.verification_status = 'verified') AS households,
                  (SELECT COALESCE(SUM(p.amount), 0) FROM point_ledger p JOIN users u ON u.id = p.user_id
                   WHERE u.neighbourhood_id = n.id AND p.status = 'released' AND p.kind <> 'redeem') AS points,
                  s.open, s.cleaned, s.avg_dirtiness
           FROM neighbourhoods n CROSS JOIN LATERAL (
               SELECT count(*) FILTER (WHERE r.status IN ('open', 'in_progress')) AS open,
                      count(*) FILTER (WHERE r.status = 'clean') AS cleaned,
                      round(avg(r.dirtiness) FILTER (WHERE r.status IN ('open', 'in_progress')), 1)::float8
                          AS avg_dirtiness
               FROM reports r
               WHERE n.boundary IS NOT NULL AND ST_Covers(n.boundary, r.location)) s
           ORDER BY points DESC, n.name"""))


@bp.get("/admin/redemptions")
@staff_required
def redemptions():
    """Vouchers from the points shop, newest first, so staff can honour and check them."""
    rows = query(
        """SELECT p.id, p.amount AS cost, p.detail, p.created_at, p.honoured_at, u.name, u.phone
           FROM point_ledger p JOIN users u ON u.id = p.user_id
           WHERE p.kind = 'redeem' ORDER BY p.created_at DESC LIMIT 200""")
    out = []
    for r in rows:
        code, _, voucher = (r.pop("detail") or "").partition(":")
        out.append({**r, "reward": code, "reward_name": REWARDS.get(code, (code,))[0],
                    "voucher": voucher, "created_at": r["created_at"].isoformat(),
                    "honoured_at": r["honoured_at"].isoformat() if r["honoured_at"] else None})
    return jsonify(out)


@bp.post("/admin/redemptions/<int:redemption_id>/honour")
@staff_required
def honour(redemption_id):
    """Staff hand the reward over: a voucher works once, so a screenshot cannot be used again."""
    row = query("""UPDATE point_ledger SET honoured_at = now()
                   WHERE id = %s AND kind = 'redeem' AND honoured_at IS NULL RETURNING honoured_at""",
                (redemption_id,), one=True)
    if row is None:
        return jsonify({"error": "voucher_used", "message": reason("voucher_used")}), 409
    return jsonify({"ok": True, "honoured_at": row["honoured_at"].isoformat()})


# ---------------------------------------------------------------- pins & directives
PIN_COLUMNS = """p.id, p.creator_id, p.title, p.description, p.category, p.status,
    p.target_count, p.reward_points, p.send_notification, p.created_at,
    p.neighbourhood_id, n.name AS neighbourhood_name,
    ST_Y(p.location::geometry) AS lat, ST_X(p.location::geometry) AS lon"""


def pin_json(row):
    out = dict(row)
    if out.get("created_at") is not None:
        out["created_at"] = out["created_at"].isoformat()
    return out


@bp.post("/admin/pins")
@staff_required
def create_pin():
    """Create a designated pin on the map (tree planting, dirty spot, watering point) and broadcast alert."""
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category = data.get("category")
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "invalid_coordinates", "message": "پۆوتانەکان هەڵەن"}), 400

    if not title or not description or category not in ("tree_planting", "cleanup_target", "watering_point"):
        return jsonify({"error": "missing_fields", "message": "تکایە هەموو زانیارییەکان بە دروستی پڕبکەرەوە"}), 400

    target_count = int(data.get("target_count") or 1)
    reward_points = int(data.get("reward_points") or 50)
    send_notification = bool(data.get("send_notification", True))

    neighbourhood_id = data.get("neighbourhood_id")
    if not neighbourhood_id:
        hood = query(
            """SELECT id FROM neighbourhoods
               WHERE boundary IS NOT NULL AND ST_Covers(boundary, ST_MakePoint(%s, %s)::geography)
               LIMIT 1""",
            (lon, lat), one=True)
        if hood:
            neighbourhood_id = hood["id"]

    pin = query(
        """INSERT INTO pins (creator_id, title, description, category, location, target_count,
                              reward_points, neighbourhood_id, send_notification)
            VALUES (%s, %s, %s, %s, ST_MakePoint(%s, %s)::geography, %s, %s, %s, %s)
            RETURNING id""",
        (g.user["id"], title, description, category, lon, lat, target_count, reward_points,
         neighbourhood_id, send_notification),
        one=True,
    )

    if send_notification:
        cat_prefixes = {
            "tree_planting": "🌱 دەستپێشخەریی نەمام ناشتن",
            "cleanup_target": "⚠️ ئاگاداری: شوێنی پاشماوە و پیسی",
            "watering_point": "💧 خاڵی ئاودان و چاودێری",
        }
        prefix = cat_prefixes.get(category, "ئاگاداریی شارەوانی")
        notif_title = f"{prefix}: {title}"
        notif_msg = f"{description} — پاداشت: {reward_points} خاڵ"
        query(
            """INSERT INTO notifications (title, message, category, pin_id, target_neighbourhood_id)
               VALUES (%s, %s, %s, %s, %s)""",
            (notif_title, notif_msg, category, pin["id"], neighbourhood_id)
        )

    saved = query(
        f"""SELECT {PIN_COLUMNS} FROM pins p
            LEFT JOIN neighbourhoods n ON n.id = p.neighbourhood_id
            WHERE p.id = %s""",
        (pin["id"],), one=True)
    return jsonify({"ok": True, "pin": pin_json(saved)}), 201


@bp.get("/admin/pins")
@staff_required
def list_admin_pins():
    rows = query(
        f"""SELECT {PIN_COLUMNS}, u.name AS creator_name,
                   COALESCE(COUNT(pr.id) FILTER (WHERE pr.status = 'registered'), 0)::int AS participant_count
            FROM pins p
            LEFT JOIN neighbourhoods n ON n.id = p.neighbourhood_id
            LEFT JOIN users u ON u.id = p.creator_id
            LEFT JOIN pin_registrations pr ON pr.pin_id = p.id
            GROUP BY p.id, n.name, u.name
            ORDER BY p.created_at DESC LIMIT 200""")
    return jsonify([pin_json(r) for r in rows])


@bp.get("/admin/pins/<int:pin_id>/participants")
@staff_required
def get_pin_participants(pin_id):
    pin = query("SELECT id, title, category, target_count FROM pins WHERE id = %s", (pin_id,), one=True)
    if not pin:
        return error("not_found", 404)
    rows = query(
        """SELECT pr.id, pr.user_id, pr.notes, pr.status, pr.created_at,
                  u.name AS user_name, u.phone AS user_phone,
                  n.name AS neighbourhood_name
           FROM pin_registrations pr
           JOIN users u ON u.id = pr.user_id
           LEFT JOIN neighbourhoods n ON n.id = u.neighbourhood_id
           WHERE pr.pin_id = %s
           ORDER BY pr.created_at ASC""",
        (pin_id,))
    out = []
    for r in rows:
        item = dict(r)
        if item.get("created_at") is not None:
            item["created_at"] = item["created_at"].isoformat()
        out.append(item)
    return jsonify({
        "pin": dict(pin),
        "count": len(out),
        "participants": out
    })



@bp.delete("/admin/pins/<int:pin_id>")
@staff_required
def delete_pin(pin_id):
    query("DELETE FROM pins WHERE id = %s", (pin_id,))
    return jsonify({"ok": True})


@bp.post("/admin/pins/<int:pin_id>/toggle")
@staff_required
def toggle_pin(pin_id):
    pin = query("SELECT status FROM pins WHERE id = %s", (pin_id,), one=True)
    if not pin:
        return error("not_found", 404)
    new_status = "completed" if pin["status"] == "active" else "active"
    query("UPDATE pins SET status = %s WHERE id = %s", (new_status, pin_id))
    return jsonify({"ok": True, "status": new_status})


# ---------------------------------------------------------------- trash bins

@bp.get("/admin/bins")
@staff_required
def list_admin_bins():
    rows = query(
        f"""SELECT {BIN_COLUMNS}
            FROM trash_bins b
            LEFT JOIN neighbourhoods n ON n.id = b.neighbourhood_id
            ORDER BY b.created_at DESC LIMIT 300"""
    )
    bins_data = [bin_json(r) for r in rows]
    stats = query(
        """SELECT
             (SELECT count(*) FROM trash_bins) AS total,
             (SELECT count(*) FROM trash_bins WHERE status = 'active') AS active,
             (SELECT count(*) FROM trash_bins WHERE status = 'full') AS full,
             (SELECT count(*) FROM bin_disposals) AS disposals""",
        one=True,
    )
    return jsonify({
        "bins": bins_data,
        "stats": {
            "total": int(stats["total"] or 0),
            "active": int(stats["active"] or 0),
            "full": int(stats["full"] or 0),
            "disposals": int(stats["disposals"] or 0),
        }
    })


@bp.post("/admin/bins")
@staff_required
def create_admin_bin():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    bin_type = data.get("bin_type") or "general"
    capacity = int(data.get("capacity_liters") or 240)
    lat = data.get("lat")
    lon = data.get("lon")

    if not name or lat is None or lon is None:
        return jsonify({"error": "missing_fields", "message": "تکایە ناو و شوێنی تەنەکەکە بە دروستی دیاریبکە"}), 400

    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return jsonify({"error": "invalid_coords", "message": "پۆوتانەکان دروست نین"}), 400

    neighbourhood_id = data.get("neighbourhood_id")
    if not neighbourhood_id:
        hood = query(
            """SELECT id FROM neighbourhoods
               WHERE boundary IS NOT NULL AND ST_Covers(boundary, ST_MakePoint(%s, %s)::geography)
               LIMIT 1""",
            (lon, lat), one=True)
        if hood:
            neighbourhood_id = hood["id"]

    # Generate unique code like GL-BIN-001, GL-BIN-002...
    custom_code = (data.get("code") or "").strip().upper()
    if custom_code:
        bin_code = custom_code
    else:
        last = query("SELECT id FROM trash_bins ORDER BY id DESC LIMIT 1", one=True)
        next_id = (last["id"] + 1) if last else 1
        bin_code = f"GL-BIN-{next_id:03d}"
        existing = query("SELECT id FROM trash_bins WHERE code = %s", (bin_code,), one=True)
        offset = 1
        while existing:
            bin_code = f"GL-BIN-{next_id + offset:03d}"
            existing = query("SELECT id FROM trash_bins WHERE code = %s", (bin_code,), one=True)
            offset += 1

    created = query(
        """INSERT INTO trash_bins (code, name, bin_type, capacity_liters, status, location,
                                    neighbourhood_id, qr_code_data)
           VALUES (%s, %s, %s, %s, 'active', ST_MakePoint(%s, %s)::geography, %s, %s)
           RETURNING id""",
        (bin_code, name, bin_type, capacity, lon, lat, neighbourhood_id, bin_code),
        one=True,
    )

    saved = query(
        f"""SELECT {BIN_COLUMNS}
            FROM trash_bins b
            LEFT JOIN neighbourhoods n ON n.id = b.neighbourhood_id
            WHERE b.id = %s""",
        (created["id"],), one=True)

    return jsonify({"ok": True, "bin": bin_json(saved)}), 201


@bp.get("/admin/bins/<int:bin_id>/sticker")
@staff_required
def download_bin_sticker(bin_id):
    from flask import Response
    b = query(
        """SELECT b.code, b.name, b.bin_type, n.name AS neighbourhood_name
           FROM trash_bins b LEFT JOIN neighbourhoods n ON n.id = b.neighbourhood_id
           WHERE b.id = %s""",
        (bin_id,), one=True)
    if not b:
        return error("not_found", 404)

    png_bytes = generate_sticker_png(
        b["code"],
        name=b["name"],
        neighbourhood=b["neighbourhood_name"] or "",
        bin_type=b["bin_type"]
    )
    filename = f"{b['code']}-sticker.png"
    return Response(
        png_bytes,
        mimetype="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@bp.delete("/admin/bins/<int:bin_id>")
@staff_required
def delete_bin(bin_id):
    query("DELETE FROM trash_bins WHERE id = %s", (bin_id,))
    return jsonify({"ok": True})


@bp.post("/admin/bins/<int:bin_id>/status")
@staff_required
def update_bin_status(bin_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in ("active", "full", "maintenance"):
        return error("invalid_status", 400)
    query("UPDATE trash_bins SET status = %s WHERE id = %s", (new_status, bin_id))
    return jsonify({"ok": True, "status": new_status})


# ---------------------------------------------------------------- households and businesses
# Staff check each place before it counts and credit verified ones a monthly amount (app/accounts.py).
# Staff see a household's location here, to check it, but homes are never drawn on the dashboard map.
STAFF_PLACE_COLUMNS = accounts.PLACE_COLUMNS + """, u.id AS owner_id, u.name AS owner_name,
    u.phone AS owner_phone, u.email AS owner_email"""
PLACES_FROM = """places p JOIN users u ON u.id = p.owner_id LEFT JOIN neighbourhoods n ON n.id = p.neighbourhood_id"""


def staff_place_json(row):
    out = accounts.place_json(row)
    out.update({k: row[k] for k in ("owner_id", "owner_name", "owner_phone", "owner_email")})
    if row["kind"] == "business":
        out["category_name"] = CATEGORY_NAMES.get(row["category"], row["category"])
    return out


@bp.get("/admin/places")
@staff_required
def places_queue():
    """?status=pending (the default), verified, rejected or all; oldest first."""
    status = request.args.get("status", "pending")
    statuses = ["pending", "verified", "rejected"] if status == "all" else [status]
    rows = query(f"""SELECT {STAFF_PLACE_COLUMNS} FROM {PLACES_FROM}
                     WHERE p.verification_status = ANY(%s) ORDER BY p.created_at, p.id LIMIT 500""", (statuses,))
    return jsonify([staff_place_json(r) for r in rows])


@bp.post("/admin/places/<int:place_id>/review")
@staff_required
def review_place(place_id):
    """{decision: verify|reject, reason?, updated_at?}. Rejecting needs a reason: the owner reads it in the
    app. A place can be reviewed again (a mistake, a fixed licence); every decision stays in place_reviews.
    updated_at is the version the staff member looked at: if the owner changed the place since, the
    answer is 409 place_changed instead of approving something nobody has seen."""
    data = json_body()
    decision = data.get("decision")
    if decision not in ("verify", "reject"):
        return error("bad_decision", 400)
    note = str(data.get("reason") or "").strip()[:500] or None
    if decision == "reject" and not note:
        return error("reason_required", 400)
    status = "verified" if decision == "verify" else "rejected"
    seen = data.get("updated_at")
    row = query("""UPDATE places SET verification_status = %s, verified_by = %s, verified_at = now(),
                          rejection_reason = %s, updated_at = now()
                   WHERE id = %s AND (%s::timestamptz IS NULL OR updated_at = %s::timestamptz) RETURNING id""",
                (status, g.user["id"], note if status == "rejected" else None, place_id, seen, seen), one=True)
    if row is None:
        exists = query("SELECT 1 FROM places WHERE id = %s", (place_id,), one=True)
        return error("place_changed", 409) if exists else error("not_found", 404)
    query("INSERT INTO place_reviews (place_id, status, reason, changed_by) VALUES (%s, %s, %s, %s)",
          (place_id, status, note, g.user["id"]))
    return jsonify(staff_place_json(query(f"SELECT {STAFF_PLACE_COLUMNS} FROM {PLACES_FROM} WHERE p.id = %s",
                                          (place_id,), one=True)))


def _month(value):
    """The first day of a 'YYYY-MM' month from 2024 up to this one, else None (no paying ahead)."""
    text = str(value or "")
    if not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", text):
        return None
    month = dt.date(int(text[:4]), int(text[5:]), 1)
    return month if dt.date(2024, 1, 1) <= month <= dt.date.today().replace(day=1) else None


def _amount(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 0 < value <= current_app.config["MAX_MONTHLY_IQD"] else None


@bp.get("/admin/payments")
@staff_required
def monthly_money():
    """?month=YYYY-MM (default: this month): every verified place and what it was credited that month
    (null: not yet), the amounts the dashboard fills in, and the month's total."""
    month = _month(request.args.get("month") or dt.date.today().strftime("%Y-%m"))
    if month is None:
        return error("invalid_month", 400)
    rows = query(f"""SELECT {STAFF_PLACE_COLUMNS}, pp.amount_iqd AS paid_iqd
                     FROM {PLACES_FROM} LEFT JOIN place_payments pp ON pp.place_id = p.id AND pp.month = %s
                     -- a place paid this month and rejected later still shows, so the total adds up
                     WHERE p.verification_status = 'verified' OR pp.id IS NOT NULL
                     ORDER BY p.kind DESC, p.name""", (month,))
    places = [{**staff_place_json(r), "paid_iqd": r["paid_iqd"]} for r in rows]
    cfg = current_app.config
    return jsonify({"month": month.strftime("%Y-%m"),
                    "defaults": {"household": cfg["HOUSEHOLD_MONTHLY_IQD"], "business": cfg["BUSINESS_MONTHLY_IQD"]},
                    "places": places, "total_iqd": sum(p["paid_iqd"] or 0 for p in places)})


@bp.post("/admin/places/<int:place_id>/payments")
@staff_required
def credit_place(place_id):
    """{month: YYYY-MM, amount_iqd, note?}: this month's money for one verified place, once."""
    data = json_body()
    month, amount = _month(data.get("month")), _amount(data.get("amount_iqd"))
    if month is None:
        return error("invalid_month", 400)
    if amount is None:
        return error("invalid_amount", 400)
    place = query("SELECT verification_status FROM places WHERE id = %s FOR SHARE", (place_id,), one=True)
    if place is None:
        return error("not_found", 404)
    if place["verification_status"] != "verified":
        return error("place_not_verified", 409)
    row = query("""INSERT INTO place_payments (place_id, month, amount_iqd, note, created_by)
                   VALUES (%s, %s, %s, %s, %s) ON CONFLICT (place_id, month) DO NOTHING RETURNING id""",
                (place_id, month, amount, str(data.get("note") or "").strip()[:300] or None, g.user["id"]), one=True)
    if row is None:
        return error("already_paid", 409)
    return jsonify({"id": row["id"], "place_id": place_id, "month": month.strftime("%Y-%m"), "amount_iqd": amount}), 201


@bp.post("/admin/payments")
@staff_required
def credit_every_place():
    """{month, household_iqd, business_iqd}: every verified place not yet credited that month gets its
    kind's amount. Pressing it twice credits nobody twice."""
    data = json_body()
    month = _month(data.get("month"))
    household, business = _amount(data.get("household_iqd")), _amount(data.get("business_iqd"))
    if month is None:
        return error("invalid_month", 400)
    if household is None or business is None:
        return error("invalid_amount", 400)
    rows = query("""INSERT INTO place_payments (place_id, month, amount_iqd, created_by)
                    SELECT id, %s, CASE kind WHEN 'household' THEN %s ELSE %s END, %s
                    FROM places WHERE verification_status = 'verified'
                    ON CONFLICT (place_id, month) DO NOTHING RETURNING id""",
                 (month, household, business, g.user["id"]))
    return jsonify({"month": month.strftime("%Y-%m"), "credited": len(rows)})
