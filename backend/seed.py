"""Create the tables and add Slemani neighbourhoods plus one municipality staff account.

    python seed.py            # uses DATABASE_URL
    STAFF_PHONE=... STAFF_PASSWORD=... python seed.py
"""
import os
from pathlib import Path

import psycopg
from werkzeug.security import generate_password_hash

from app.config import Config

NEIGHBOURHOODS = ["سەرچنار", "بەختیاری", "ئازادی", "ڕاپەڕین", "کانی ئاسکان", "زەرگەتە"]


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
            (staff_phone or os.environ.get("STAFF_PHONE", "07500000000"),
             generate_password_hash(staff_password or os.environ.get("STAFF_PASSWORD", "staff1234"))),
        )


if __name__ == "__main__":
    seed()
    print("Database ready: tables, neighbourhoods and one staff account.")
