"""One PostgreSQL connection per request; committed at the end unless the request failed."""
from contextlib import contextmanager

import psycopg
from flask import current_app, g
from psycopg.rows import dict_row


def get_db():
    if "db" not in g:
        g.db = psycopg.connect(current_app.config["DATABASE_URL"], row_factory=dict_row)
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is None:
        return
    if error is None:
        db.commit()
    else:
        db.rollback()
    db.close()


@contextmanager
def savepoint():
    """Undo only this block when it raises (a duplicate phone, say), so the request can still answer
    and write. Never commits: the request's one transaction still ends in close_db. (psycopg's own
    transaction() would BEGIN and COMMIT here if no statement had run yet in this request.)"""
    db = get_db()
    db.execute("SAVEPOINT block")
    try:
        yield
    except Exception:
        db.execute("ROLLBACK TO SAVEPOINT block")
        raise
    db.execute("RELEASE SAVEPOINT block")


def query(sql, params=(), one=False):
    cur = get_db().execute(sql, params)
    if cur.description is None:
        return None
    return cur.fetchone() if one else cur.fetchall()


def housekeeping():
    """Cheap upkeep run before reads: release matured points, reopen abandoned claims."""
    db = get_db()
    db.execute(
        """UPDATE point_ledger SET status = 'released'
           WHERE status = 'pending' AND release_at IS NOT NULL AND release_at <= now()"""
    )
    db.execute(
        """UPDATE reports r SET status = 'open'
           WHERE r.status = 'in_progress' AND NOT EXISTS (
               SELECT 1 FROM challenges c
               WHERE c.report_id = r.id AND NOT c.used AND c.expires_at > now())"""
    )
