"""Points shop and daily tasks. In the build plan these are the first things to drop when time is
short, so they sit in their own blueprint and nothing else depends on them.

Shop: released points buy a reward; the ledger gets a 'redeem' row and the person a voucher code.
Tasks: three small goals a day; finishing one lets you claim a small bonus once, held 24 hours.
"""
import secrets

import psycopg
from flask import Blueprint, current_app, g, jsonify

from . import points
from .auth import error, login_required
from .db import housekeeping, query
from .strings import REWARDS, TASKS, reason

bp = Blueprint("rewards", __name__)


def _vouchers(user_id):
    rows = query(
        """SELECT amount, detail, created_at FROM point_ledger
           WHERE user_id = %s AND kind = 'redeem' ORDER BY created_at DESC LIMIT 20""",
        (user_id,))
    out = []
    for r in rows:
        code, _, voucher = (r["detail"] or "").partition(":")
        out.append({"reward": code, "name": REWARDS.get(code, (code,))[0], "cost": r["amount"],
                    "voucher": voucher, "created_at": r["created_at"].isoformat()})
    return out


@bp.get("/rewards")
@login_required
def catalogue():
    housekeeping()
    items = [{"code": code, "name": REWARDS[code][0], "description": REWARDS[code][1], "cost": cost}
             for code, cost in sorted(current_app.config["REWARDS"].items(), key=lambda kv: kv[1])]
    return jsonify({"rewards": items, "balance": points.balance(g.user["id"])["released"],
                    "vouchers": _vouchers(g.user["id"])})


@bp.post("/rewards/<code>/redeem")
@login_required
def redeem(code):
    cost = current_app.config["REWARDS"].get(code)
    if cost is None or code not in REWARDS:
        return error("unknown_reward", 404)
    # One redemption at a time per person: two taps at once must not spend the same points twice.
    query("SELECT id FROM users WHERE id = %s FOR UPDATE", (g.user["id"],))
    housekeeping()
    balance = points.balance(g.user["id"])["released"]
    if balance < cost:
        return error("not_enough_points", 409)
    voucher = "GL-" + secrets.token_hex(3).upper()
    points.add(g.user["id"], cost, "redeem", "released", detail=f"{code}:{voucher}")
    return jsonify({"reward": code, "name": REWARDS[code][0], "cost": cost, "voucher": voucher,
                    "balance": balance - cost, "message": reason("redeemed")}), 201


def _progress(user_id):
    """How far the person got today on each task, plus today's date as the claim key."""
    return query(
        """SELECT
             (SELECT count(*) FROM point_ledger WHERE user_id = %(u)s AND kind = 'report'
                AND status <> 'revoked' AND created_at >= date_trunc('day', now())) AS report,
             (SELECT count(*) FROM point_ledger WHERE user_id = %(u)s AND kind = 'confirmation'
                AND status <> 'revoked' AND created_at >= date_trunc('day', now())) AS confirm,
             (SELECT count(*) FROM cleanups WHERE cleaner_id = %(u)s AND verdict = 'verified'
                AND created_at >= date_trunc('day', now())) AS cleanup,
             to_char(now(), 'YYYY-MM-DD') AS day""",
        {"u": user_id}, one=True)


def _claimed(user_id, day):
    rows = query("SELECT detail FROM point_ledger WHERE user_id = %s AND kind = 'task' AND detail LIKE %s",
                 (user_id, f"task:%:{day}"))
    return {r["detail"].split(":")[1] for r in rows}


@bp.get("/tasks")
@login_required
def daily_tasks():
    progress = _progress(g.user["id"])
    claimed = _claimed(g.user["id"], progress["day"])
    tasks = []
    for code, (target, bonus) in current_app.config["DAILY_TASKS"].items():
        done = min(progress[code], target)
        tasks.append({"code": code, "title": TASKS[code], "target": target, "done": done,
                      "bonus": bonus, "complete": done >= target, "claimed": code in claimed})
    return jsonify({"day": progress["day"], "tasks": tasks})


@bp.post("/tasks/<code>/claim")
@login_required
def claim_task(code):
    task = current_app.config["DAILY_TASKS"].get(code)
    if task is None or code not in TASKS:
        return error("unknown_task", 404)
    target, bonus = task
    progress = _progress(g.user["id"])
    if progress[code] < target:
        return error("task_not_done", 409)
    if code in _claimed(g.user["id"], progress["day"]):
        return error("task_already_claimed", 409)
    try:
        points.add(g.user["id"], bonus, "task", "pending", detail=f"task:{code}:{progress['day']}",
                   release_in_hours=current_app.config["HOLD_HOURS"])
    except psycopg.errors.UniqueViolation:     # a second tap that raced the first
        return error("task_already_claimed", 409)
    return jsonify({"code": code, "points_pending": bonus, "message": reason("task_claimed")}), 201
