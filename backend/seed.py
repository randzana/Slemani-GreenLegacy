"""Create the tables and add Slemani neighbourhoods plus one municipality staff account.

    python seed.py            # uses DATABASE_URL
    STAFF_PHONE=... STAFF_PASSWORD=... python seed.py

Without STAFF_PASSWORD the staff password is staff1234, which is printed in the README: fine for
practice, but anyone who has read it can open the dashboard and approve cleanups.
"""
import os
from pathlib import Path

import psycopg
from werkzeug.security import generate_password_hash

from app.config import Config

NEIGHBOURHOODS = ["سەرچنار", "بەختیاری", "ئازادی", "ڕاپەڕین", "کانی ئاسکان", "زەرگەتە"]
DEFAULT_STAFF_PHONE, DEFAULT_STAFF_PASSWORD = "07500000000", "staff1234"


def seed(database_url=None, staff_phone=None, staff_password=None):
    url = database_url or Config.DATABASE_URL
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(url) as conn:
        conn.execute(schema)
        for name in NEIGHBOURHOODS:
            conn.execute("INSERT INTO neighbourhoods (name) VALUES (%s)", (name,))
        conn.execute(
            """INSERT INTO users (name, phone, password_hash, role)
               VALUES ('شارەوانیی سلێمانی', %s, %s, 'staff')""",
            (staff_phone or os.environ.get("STAFF_PHONE") or DEFAULT_STAFF_PHONE,
             # an empty STAFF_PASSWORD (a broken .env line) falls back too, never to an empty password
             generate_password_hash(staff_password or os.environ.get("STAFF_PASSWORD") or DEFAULT_STAFF_PASSWORD)),
        )


if __name__ == "__main__":
    seed()
    print("Database ready: tables, neighbourhoods and one staff account.")
    if not os.environ.get("STAFF_PASSWORD"):
        print(f"⚠ The staff password is the public default {DEFAULT_STAFF_PASSWORD}: before a demo, put "
              "STAFF_PASSWORD in .env (docs/DEMO.md) and run seed.py again.")
