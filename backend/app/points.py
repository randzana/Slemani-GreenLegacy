"""Points live in a ledger, one row per movement, so holds, caps and revoking are simple queries.

Rules from the build plan:
- no points unless the detector finds litter (enforced in the report route)
- report points scale with dirtiness and stay pending until a confirmation or a verified cleanup
- the first reporter gets full points; a second report within 30 m is a small confirmation
- a reporter cannot earn cleanup points on their own spot within 24 hours (claim route)
- report points are always lower than cleanup points
- a daily cap on rewarded reports per account
- cleanup: a small share now, the rest after a 24-hour hold
"""
from flask import current_app

from .db import query


def add(user_id, amount, kind, status, report_id=None, cleanup_id=None, release_in_hours=None,
        detail=None):
    if amount <= 0:
        return None
    release_sql = "now() + make_interval(hours => %s)" if release_in_hours is not None else "NULL"
    params = [user_id, amount, kind, status, report_id, cleanup_id, detail]
    if release_in_hours is not None:
        params.append(release_in_hours)
    return query(
        f"""INSERT INTO point_ledger (user_id, amount, kind, status, report_id, cleanup_id, detail,
                                      release_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, {release_sql}) RETURNING *""",
        params,
        one=True,
    )


def rewarded_reports_today(user_id):
    row = query(
        """SELECT count(*) AS n FROM point_ledger
           WHERE user_id = %s AND kind IN ('report', 'confirmation')
             AND created_at >= date_trunc('day', now())""",
        (user_id,),
        one=True,
    )
    return row["n"]


def under_daily_cap(user_id):
    return rewarded_reports_today(user_id) < current_app.config["DAILY_REWARDED_REPORTS"]


def award_report(user_id, report_id, dirtiness):
    amount = current_app.config["REPORT_POINTS"][dirtiness]
    return add(user_id, amount, "report", "pending", report_id=report_id)   # waits for confirmation


def award_confirmation(user_id, report_id):
    cfg = current_app.config
    return add(user_id, cfg["CONFIRMATION_POINTS"], "confirmation", "pending",
               report_id=report_id, release_in_hours=cfg["HOLD_HOURS"])


def release_report_points(report_id):
    """The spot was real (confirmed or cleaned): release the original reporter's pending points."""
    query(
        """UPDATE point_ledger SET status = 'released'
           WHERE report_id = %s AND kind = 'report' AND status = 'pending'""",
        (report_id,),
    )


def award_cleanup(user_id, report_id, cleanup_id, dirtiness, verified):
    """Verified: a small share released now, the rest held 24 h. Review: everything waits for staff."""
    cfg = current_app.config
    total = cfg["CLEANUP_POINTS"][dirtiness]
    if not verified:
        add(user_id, total, "cleanup", "pending", report_id, cleanup_id)
        return {"now": 0, "pending": total}
    now_part = int(round(total * cfg["IMMEDIATE_SHARE"]))
    add(user_id, now_part, "cleanup", "released", report_id, cleanup_id)
    add(user_id, total - now_part, "cleanup", "pending", report_id, cleanup_id,
        release_in_hours=cfg["HOLD_HOURS"])
    return {"now": now_part, "pending": total - now_part}


def approve_reviewed_cleanup(cleanup_id):
    """Staff approved: treat like a verified cleanup (share now, rest after the hold)."""
    cfg = current_app.config
    rows = query(
        "SELECT * FROM point_ledger WHERE cleanup_id = %s AND status = 'pending' AND release_at IS NULL",
        (cleanup_id,),
    )
    for row in rows:
        now_part = int(round(row["amount"] * cfg["IMMEDIATE_SHARE"]))
        query("UPDATE point_ledger SET amount = %s, status = 'released' WHERE id = %s",
              (now_part, row["id"]))
        add(row["user_id"], row["amount"] - now_part, "cleanup", "pending", row["report_id"],
            cleanup_id, release_in_hours=cfg["HOLD_HOURS"])


def revoke_cleanup(cleanup_id):
    query("UPDATE point_ledger SET status = 'revoked' WHERE cleanup_id = %s AND status = 'pending'",
          (cleanup_id,))


def balance(user_id):
    return query(
        """SELECT
             COALESCE(SUM(amount) FILTER (WHERE status = 'released' AND kind <> 'redeem'), 0)
           - COALESCE(SUM(amount) FILTER (WHERE status = 'released' AND kind = 'redeem'), 0) AS released,
             COALESCE(SUM(amount) FILTER (WHERE status = 'pending'), 0) AS pending,
             -- everything ever earned (spending does not lower levels, badges or the league)
             COALESCE(SUM(amount) FILTER (WHERE status = 'released' AND kind <> 'redeem'), 0) AS earned
           FROM point_ledger WHERE user_id = %s""",
        (user_id,),
        one=True,
    )


def adjust_trust(user_id, event):
    """Move the person's trust score by the amount set for this outcome (config.TRUST_DELTAS)."""
    delta = current_app.config["TRUST_DELTAS"].get(event)
    if delta:
        query("UPDATE users SET trust_level = trust_level + %s WHERE id = %s", (delta, user_id))


# Earned points for the league: released, never redeemed ones (spending does not lower your rank)
EARNED = "COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'released' AND p.kind <> 'redeem'), 0)"


def ranks(user_id, neighbourhood_id):
    """The person's place among citizens and their neighbourhood's place in the league."""
    return query(
        f"""WITH people AS (
                SELECT u.id, RANK() OVER (ORDER BY {EARNED} DESC) AS rank
                FROM users u LEFT JOIN point_ledger p ON p.user_id = u.id
                WHERE u.role = 'citizen' GROUP BY u.id),
            hoods AS (
                SELECT n.id, RANK() OVER (ORDER BY {EARNED} DESC) AS rank
                FROM neighbourhoods n
                LEFT JOIN users u ON u.neighbourhood_id = n.id
                LEFT JOIN point_ledger p ON p.user_id = u.id
                GROUP BY n.id)
            SELECT (SELECT rank FROM people WHERE id = %s) AS rank,
                   (SELECT count(*) FROM people) AS citizens,
                   (SELECT rank FROM hoods WHERE id = %s) AS neighbourhood_rank,
                   (SELECT count(*) FROM hoods) AS neighbourhoods""",
        (user_id, neighbourhood_id),
        one=True,
    )
