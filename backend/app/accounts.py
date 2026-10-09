"""Accounts: the person (users) and the household and business they may add (places).

Signing up with a password (app/auth.py) and with Google both end in create_account(), so the rules
live in one place:
- Everything is checked before the first INSERT. close_db commits a request that *returns* an error,
  so a check that failed after the user row was written would leave half an account behind.
- The user and their places are written in one savepoint: a phone or email that is already taken
  undoes all of it and comes back as an error code.
- A place's neighbourhood comes from its location when boundaries are loaded, else from the form.
- A household's location is private. It leaves the server only in its owner's /me and in staff
  pages; nothing public lists places at all.
- Changing what staff checked (REVIEWED_FIELDS) sends a verified place back to the queue, and any
  change to a rejected place resubmits it. Every status change is kept in place_reviews.
"""
import math

import psycopg
from flask import current_app

from .db import query, savepoint

KINDS = ("household", "business")
CATEGORIES = ("restaurant", "cafe", "shop", "supermarket", "bakery", "hotel", "workshop", "other")
PLACE_FIELDS = {
    "household": {"name", "residents_count", "address", "lat", "lon", "neighbourhood_id"},
    "business": {"name", "category", "license_number", "address", "lat", "lon", "neighbourhood_id"},
}
REVIEWED_FIELDS = {"household": ("name", "residents_count", "location"),
                   "business": ("name", "category", "license_number", "location")}
NAME_MAX = 80
MAX_ID = 2**31 - 1
TAKEN = {"users_phone_key": "phone_taken", "users_email_key_unique": "email_taken",
         "user_identities_provider_subject_key": "google_already_linked"}

PLACE_COLUMNS = """p.id, p.kind, p.name, p.address, p.residents_count, p.category, p.license_number,
    p.neighbourhood_id, n.name AS neighbourhood, p.verification_status, p.rejection_reason,
    p.verified_at, p.created_at, p.updated_at,
    ST_Y(p.location::geometry) AS lat, ST_X(p.location::geometry) AS lon"""
# the neighbourhood whose boundary covers a point (%s = lon, lat), when boundaries are loaded
COVERING = """(SELECT id FROM neighbourhoods WHERE boundary IS NOT NULL
               AND ST_Covers(boundary, ST_MakePoint(%s, %s)::geography) ORDER BY id LIMIT 1)"""


# ---------------------------------------------------------------- checking what the phone sent

def _text(data, key, field, errors, required=False, low=0, high=None):
    value = data.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors[field] = "required"
        return None
    if not isinstance(value, str):
        errors[field] = "invalid"
        return None
    value = value.strip()
    if len(value) < low:
        errors[field] = "too_short"
    elif high and len(value) > high:
        errors[field] = "too_long"
    return value


def _number(value):
    """A finite JSON number, else None (true/false are not numbers here)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _whole(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def known_neighbourhood(value):
    value = _whole(value)
    return (value is not None and 0 < value <= MAX_ID
            and query("SELECT 1 FROM neighbourhoods WHERE id = %s", (value,), one=True) is not None)


def in_service_area(lat, lon):
    min_lat, min_lon, max_lat, max_lon = current_app.config["SERVICE_AREA_BBOX"]
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def validate_place(kind, data):
    """(place, {}) or (None, {"<kind>.<field>": problem}). Unknown fields are refused, so a household
    sent as a business, or a typo, is an error instead of being dropped without a word."""
    if not isinstance(data, dict):
        return None, {kind: "invalid"}
    errors = {f"{kind}.{key}": "unknown_field" for key in data if key not in PLACE_FIELDS[kind]}
    place = {"kind": kind,
             "name": _text(data, "name", f"{kind}.name", errors, required=True, low=2, high=120),
             "address": _text(data, "address", f"{kind}.address", errors, high=300),
             "residents_count": None, "category": None, "license_number": None}
    if kind == "household":
        count = data.get("residents_count")
        if count is None:
            errors["household.residents_count"] = "required"
        elif _whole(count) is None or not 1 <= count <= 30:
            errors["household.residents_count"] = "invalid"
        place["residents_count"] = count
    else:
        category = data.get("category")
        if category is None:
            errors["business.category"] = "required"
        elif category not in CATEGORIES:
            errors["business.category"] = "invalid"
        place["category"] = category
        place["license_number"] = _text(data, "license_number", "business.license_number", errors, high=64)

    lat, lon = _number(data.get("lat")), _number(data.get("lon"))
    if data.get("lat") is None or data.get("lon") is None:
        errors[f"{kind}.location"] = "required"
    elif lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        errors[f"{kind}.location"] = "invalid"
    elif not in_service_area(lat, lon):
        errors[f"{kind}.location"] = "outside_service_area"
    place["lat"], place["lon"] = lat, lon

    hood = data.get("neighbourhood_id")
    if hood is not None and not known_neighbourhood(hood):
        errors[f"{kind}.neighbourhood_id"] = "unknown"
    place["neighbourhood_id"] = hood
    return (None, errors) if errors else (place, {})


def validate_signup(data):
    """The parts of a sign-up body beyond name, phone and password: ({...}, {}) or (None, errors)."""
    errors = {}
    if len(str(data.get("name") or "").strip()) > NAME_MAX:
        errors["name"] = "too_long"
    hood = data.get("neighbourhood_id")
    if hood is not None and not known_neighbourhood(hood):
        errors["neighbourhood_id"] = "unknown"
    places = []
    for kind in KINDS:
        if data.get(kind) is not None:
            place, problems = validate_place(kind, data[kind])
            errors.update(problems)
            if place:
                places.append(place)
    return (None, errors) if errors else ({"neighbourhood_id": hood, "places": places}, {})


# ---------------------------------------------------------------- writing

def create_account(name, phone, password_hash, neighbourhood_id=None, email=None, email_key=None, places=(),
                   google_sub=None):
    """Write a checked person, their checked places and (signing up with Google) their Google identity.
    (user, None), or (None, 'phone_taken' / 'email_taken' / 'google_already_linked') with nothing
    written at all."""
    try:
        with savepoint():
            user = query(
                """INSERT INTO users (name, phone, password_hash, neighbourhood_id, email, email_key,
                                      email_verified_at)
                   VALUES (%(name)s, %(phone)s, %(hash)s, %(hood)s, %(email)s, %(key)s,
                           CASE WHEN %(email)s::text IS NULL THEN NULL ELSE now() END)
                   RETURNING *""",
                {"name": name, "phone": phone, "hash": password_hash, "hood": neighbourhood_id,
                 "email": email, "key": email_key}, one=True)
            if google_sub:
                query("""INSERT INTO user_identities (user_id, provider, subject, email, last_login_at)
                         VALUES (%s, 'google', %s, %s, now())""", (user["id"], google_sub, email))
            for place in places:
                _insert_place(user["id"], place)
            if user["neighbourhood_id"] is None and places:
                # no neighbourhood chosen: the household's (or else the business's) is a good guess
                user = query(
                    """UPDATE users SET neighbourhood_id = (
                           SELECT neighbourhood_id FROM places WHERE owner_id = %s AND neighbourhood_id IS NOT NULL
                           ORDER BY kind = 'household' DESC LIMIT 1)
                       WHERE id = %s RETURNING *""", (user["id"], user["id"]), one=True)
    except psycopg.errors.UniqueViolation as exc:
        taken = TAKEN.get(exc.diag.constraint_name)
        if taken is None:
            raise
        return None, taken
    return user, None


def _insert_place(owner_id, place):
    row = query(
        f"""INSERT INTO places (owner_id, kind, name, address, location, neighbourhood_id,
                                residents_count, category, license_number)
            VALUES (%s, %s, %s, %s, ST_MakePoint(%s, %s)::geography, COALESCE({COVERING}, %s), %s, %s, %s)
            RETURNING id""",
        (owner_id, place["kind"], place["name"], place["address"], place["lon"], place["lat"],
         place["lon"], place["lat"], place["neighbourhood_id"], place["residents_count"],
         place["category"], place["license_number"]), one=True)
    query("INSERT INTO place_reviews (place_id, status, changed_by) VALUES (%s, 'pending', %s)",
          (row["id"], owner_id))
    return row["id"]


def _changed(existing, place, field):
    if field == "location":     # 1e-7 degrees is about a centimetre: the same pin sent back
        return abs(existing["lat"] - place["lat"]) > 1e-7 or abs(existing["lon"] - place["lon"]) > 1e-7
    return existing[field] != place[field]


def save_place(owner_id, place):
    """Add the person's household or business, or change it. Returns (place as the owner sees it,
    created?). Edits by one person take turns, so two taps cannot add the same kind twice."""
    query("SELECT 1 FROM users WHERE id = %s FOR UPDATE", (owner_id,))
    existing = query(f"""SELECT {PLACE_COLUMNS} FROM places p LEFT JOIN neighbourhoods n ON n.id = p.neighbourhood_id
                         WHERE p.owner_id = %s AND p.kind = %s""", (owner_id, place["kind"]), one=True)
    if existing is None:
        place_id = _insert_place(owner_id, place)
        return owner_place(place_id), True

    status = existing["verification_status"]
    resubmit = status == "rejected" or (
        status == "verified" and any(_changed(existing, place, f) for f in REVIEWED_FIELDS[place["kind"]]))
    query(
        f"""UPDATE places SET name = %s, address = %s, location = ST_MakePoint(%s, %s)::geography,
                   neighbourhood_id = COALESCE({COVERING}, %s), residents_count = %s, category = %s,
                   license_number = %s, updated_at = now(),
                   verification_status = CASE WHEN %s THEN 'pending' ELSE verification_status END,
                   verified_by = CASE WHEN %s THEN NULL ELSE verified_by END,
                   verified_at = CASE WHEN %s THEN NULL ELSE verified_at END,
                   rejection_reason = CASE WHEN %s THEN NULL ELSE rejection_reason END
            WHERE id = %s""",
        (place["name"], place["address"], place["lon"], place["lat"], place["lon"], place["lat"],
         place["neighbourhood_id"], place["residents_count"], place["category"], place["license_number"],
         resubmit, resubmit, resubmit, resubmit, existing["id"]))
    if resubmit:
        query("INSERT INTO place_reviews (place_id, status, changed_by) VALUES (%s, 'pending', %s)",
              (existing["id"], owner_id))
    return owner_place(existing["id"]), False


# ---------------------------------------------------------------- reading (owner and staff only)

def place_json(row):
    """A place with its location: only for its owner and for staff, never for a public list."""
    out = {k: row[k] for k in ("id", "kind", "name", "address", "neighbourhood_id", "neighbourhood",
                               "verification_status", "rejection_reason", "lat", "lon")}
    if row["kind"] == "household":
        out["residents_count"] = row["residents_count"]
    else:
        out["category"], out["license_number"] = row["category"], row["license_number"]
    for key in ("verified_at", "created_at", "updated_at"):
        out[key] = row[key].isoformat() if row[key] else None
    return out


def owner_place(place_id):
    return place_json(query(f"""SELECT {PLACE_COLUMNS} FROM places p
                                LEFT JOIN neighbourhoods n ON n.id = p.neighbourhood_id WHERE p.id = %s""",
                            (place_id,), one=True))


def owner_places(owner_id):
    return [place_json(r) for r in query(
        f"""SELECT {PLACE_COLUMNS} FROM places p LEFT JOIN neighbourhoods n ON n.id = p.neighbourhood_id
            WHERE p.owner_id = %s ORDER BY p.kind DESC""", (owner_id,))]


def money(owner_id):
    """The monthly money staff credited to the person's places: a number for now, paid out later."""
    rows = query("""SELECT pp.place_id, p.kind, pp.month, pp.amount_iqd FROM place_payments pp
                    JOIN places p ON p.id = pp.place_id WHERE p.owner_id = %s
                    ORDER BY pp.month DESC, p.kind DESC LIMIT 24""", (owner_id,))
    total = query("""SELECT COALESCE(SUM(pp.amount_iqd), 0) AS total FROM place_payments pp
                     JOIN places p ON p.id = pp.place_id WHERE p.owner_id = %s""", (owner_id,), one=True)
    return {"total_iqd": int(total["total"]),
            "payments": [{**r, "month": r["month"].isoformat()} for r in rows]}


def auth_methods(user):
    google = query("SELECT 1 FROM user_identities WHERE user_id = %s AND provider = 'google'",
                   (user["id"],), one=True)
    return (["password"] if user["password_hash"] else []) + (["google"] if google else [])
