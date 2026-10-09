"""Migration 007 on a database from before it: afterwards it has exactly the schema a fresh seed has, the
data is kept, phones are in one form and old accounts still log in. When two accounts are one phone
written two ways it stops and changes nothing."""
from pathlib import Path

import psycopg
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.ai.detector import ColorBlobDetector
from conftest import STAFF, TEST_DB
from seed import seed
from tools import preflight

HERE = Path(__file__).resolve().parent
MIGRATION_007 = (HERE.parent / "migrations" / "007_accounts_email_google.sql").read_text(encoding="utf-8")
SCHEMA_006 = (HERE / "fixtures" / "schema_006.sql").read_text(encoding="utf-8")


def fingerprint(conn):
    """Every column, constraint, index and geography type: what a migration has to get right.
    Column order is left out: ALTER TABLE ADD COLUMN can only append."""
    return {
        "columns": set(conn.execute(
            """SELECT table_name, column_name, data_type, udt_name, is_nullable, column_default
               FROM information_schema.columns WHERE table_schema = current_schema()""").fetchall()),
        "constraints": set(conn.execute(
            """SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid)
               FROM pg_constraint WHERE connamespace = current_schema()::regnamespace""").fetchall()),
        "indexes": set(conn.execute(
            "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = current_schema()").fetchall()),
        "geography": set(conn.execute(
            """SELECT f_table_name, f_geography_column, type, srid FROM geography_columns
               WHERE f_table_schema = current_schema()""").fetchall()),
    }


def marks(results):
    return {label: (mark, detail) for mark, label, detail in results}


@pytest.fixture()
def old_db():
    """An empty database as schema.sql made it before 007 (PostGIS's own table stays)."""
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        tables = [r[0] for r in conn.execute("""SELECT tablename FROM pg_tables WHERE schemaname = current_schema()
                                                  AND tablename <> 'spatial_ref_sys'""")]
        if tables:
            conn.execute("DROP TABLE " + ", ".join(f'"{t}"' for t in tables) + " CASCADE")
        conn.execute(SCHEMA_006)
        conn.execute("INSERT INTO neighbourhoods (name) VALUES ('سەرچنار')")
    yield TEST_DB
    seed(TEST_DB, *STAFF)          # every other test expects a normally seeded database


def add_users(conn, *phones):
    return [conn.execute("""INSERT INTO users (name, phone, password_hash, neighbourhood_id)
                            VALUES ('هاوڵاتی', %s, %s, 1) RETURNING id""",
                         (phone, generate_password_hash("secret123"))).fetchone()[0] for phone in phones]


def test_007_gives_a_fresh_seeds_schema_and_keeps_the_data(old_db):
    typed = ["07501234567", "0770 123 4567", "+9647801234567", "9647511234567", "(0790) 123-4567",
             "0533123456", "not a phone"]
    with psycopg.connect(old_db, autocommit=True) as conn:
        ids = add_users(conn, *typed)
        conn.execute("""INSERT INTO point_ledger (user_id, amount, kind, status)
                        VALUES (%s, 40, 'cleanup', 'released')""", (ids[0],))
        found = marks(preflight.check_database(old_db))
        assert found["خشتە نوێکان"][0] == preflight.FAIL and "places" in found["خشتە نوێکان"][1]
        assert "migrations/007_accounts_email_google.sql" in found["خشتە نوێکان"][1]
        assert found["ستوونە نوێکان"][0] == preflight.FAIL and "users.email" in found["ستوونە نوێکان"][1]

        conn.execute(MIGRATION_007)
        conn.execute(MIGRATION_007)                     # safe to run again
        phones = dict(conn.execute("SELECT id, phone FROM users").fetchall())
        assert [phones[i] for i in ids] == ["+9647501234567", "+9647701234567", "+9647801234567",
                                            "+9647511234567", "+9647901234567",
                                            "0533123456", "not a phone"]   # not Iraqi mobiles: left alone
        assert conn.execute("SELECT user_id, amount FROM point_ledger").fetchall() == [(ids[0], 40)]
        found = marks(preflight.check_database(old_db))
        assert found["خشتە نوێکان"][0] == found["ستوونە نوێکان"][0] == preflight.OK
        migrated = fingerprint(conn)

    # old accounts log in however they type their number, and the rows 007 left alone as they are
    client = create_app({"DATABASE_URL": old_db, "TESTING": True}, detector=ColorBlobDetector()).test_client()
    for phone in ("+9647501234567", "0750 123 4567", "07701234567", "0533123456", "not a phone"):
        r = client.post("/auth/login", json={"phone": phone, "password": "secret123"})
        assert r.status_code == 200, (phone, r.json)
    assert client.post("/auth/login", json={"phone": "07501234567", "password": "wrong!!"}).status_code == 401

    seed(old_db, *STAFF)
    with psycopg.connect(old_db) as conn:
        assert fingerprint(conn) == migrated            # old database + 007 == fresh schema.sql


def test_007_stops_and_changes_nothing_when_one_phone_has_two_accounts(old_db):
    with psycopg.connect(old_db, autocommit=True) as conn:
        first, second, _other = add_users(conn, "0750 123 4567", "+9647501234567", "07701234567")
        before = conn.execute("SELECT id, phone FROM users ORDER BY id").fetchall()
        with pytest.raises(psycopg.errors.RaiseException) as stop:
            conn.execute(MIGRATION_007)
        conn.execute("ROLLBACK")
        assert f'user #{first} "0750 123 4567"' in str(stop.value)
        assert f'user #{second} "+9647501234567"' in str(stop.value)
        assert conn.execute("SELECT id, phone FROM users ORDER BY id").fetchall() == before
        assert conn.execute("SELECT to_regclass('places')").fetchone()[0] is None
        assert conn.execute("""SELECT count(*) FROM information_schema.columns
                               WHERE table_name = 'users' AND column_name = 'email'""").fetchone()[0] == 0

        # the hint is the fix: sort the accounts out by hand, then the same file runs through
        conn.execute("DELETE FROM users WHERE id = %s", (first,))
        conn.execute(MIGRATION_007)
        assert conn.execute("SELECT phone FROM users ORDER BY id").fetchall() == [("+9647501234567",),
                                                                                 ("+9647701234567",)]
