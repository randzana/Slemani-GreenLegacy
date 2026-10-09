"""Accounts and places (app/accounts.py): one person per verified email, with an optional household
and business that staff check, whose location stays private."""
import itertools
import json

import psycopg

from conftest import TEST_DB
from test_boundaries import square
from test_flow import dirty_spot

HOME = {"name": "ماڵی ئەحمەد", "residents_count": 4, "address": "سەرچنار، کۆڵانی ٣",
        "lat": 35.567891, "lon": 45.412345}
SHOP = {"name": "کافێی سەوز", "category": "cafe", "license_number": "SUL-1234",
        "lat": 35.561234, "lon": 45.437654}


def bearer(r):
    return {"Authorization": f"Bearer {r.json['token']}"}


def sql(statement, params=()):
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else None


def form(api, email="rand@example.com", phone="07701234567", **extra):
    return {"name": "ڕەند", "phone": phone, "password": "secret123", "neighbourhood_id": 1,
            "email_verification_token": api.email_token(email), **extra}


def count(table):
    return sql(f"SELECT count(*) FROM {table}")[0][0]


# ---------------------------------------------------------------- signing up

def test_a_simple_citizen(client, api):
    r = client.post("/auth/signup", json=form(api))
    assert r.status_code == 201 and r.json["user"]["email"] == "rand@example.com"
    me = client.get("/me", headers=bearer(r)).json
    assert me["email_verified"] is True and me["auth_methods"] == ["password"]
    assert me["places"] == [] and me["money"] == {"total_iqd": 0, "payments": []}
    assert me["phone"] == "+9647701234567" and me["role"] == "citizen"


def test_a_household_and_a_business_in_one_go(client, api):
    r = client.post("/auth/signup", json=form(api, household=HOME, business=SHOP))
    assert r.status_code == 201, r.json
    places = {p["kind"]: p for p in client.get("/me", headers=bearer(r)).json["places"]}
    home, shop = places["household"], places["business"]
    assert home["verification_status"] == shop["verification_status"] == "pending"
    assert (home["name"], home["residents_count"], home["lat"], home["lon"]) == ("ماڵی ئەحمەد", 4, 35.567891, 45.412345)
    assert (shop["category"], shop["license_number"]) == ("cafe", "SUL-1234") and "residents_count" not in shop
    assert sql("SELECT status, changed_by IS NOT NULL FROM place_reviews ORDER BY id") == [("pending", True)] * 2


def test_only_a_business(client, api):
    r = client.post("/auth/signup", json=form(api, business=SHOP))
    assert [p["kind"] for p in client.get("/me", headers=bearer(r)).json["places"]] == ["business"]


def test_the_place_neighbourhood_comes_from_its_location_when_boundaries_are_loaded(client, api):
    sql("""UPDATE neighbourhoods SET boundary = ST_Multi(ST_GeomFromGeoJSON(%s))::geography WHERE id = 3""",
        (json.dumps({"type": "Polygon", "coordinates": square(HOME["lat"], HOME["lon"])}),))
    # the form says neighbourhood 2 for the home, but the boundary of 3 covers its pin
    r = client.post("/auth/signup", json=form(api, neighbourhood_id=None,
                                              household={**HOME, "neighbourhood_id": 2},
                                              business={**SHOP, "neighbourhood_id": 2}))
    places = {p["kind"]: p for p in client.get("/me", headers=bearer(r)).json["places"]}
    assert places["household"]["neighbourhood_id"] == 3          # the boundary wins
    assert places["business"]["neighbourhood_id"] == 2           # no boundary covers it: the form's
    assert r.json["user"]["neighbourhood_id"] == 3               # none chosen: the household's


def test_the_email_comes_from_the_code_never_from_the_form(client, api):
    body = form(api)
    body["email"] = "evil@example.com"
    r = client.post("/auth/signup", json=body)
    assert r.status_code == 201 and r.json["user"]["email"] == "rand@example.com"


def test_no_verified_email_no_account(client, api, app):
    body = form(api)
    for token in (None, "", "garbage", body["email_verification_token"] + "x"):
        r = client.post("/auth/signup", json={**body, "email_verification_token": token})
        assert r.status_code == 401 and r.json["error"] == "email_not_verified", token
    staff = client.post("/auth/login", json={"phone": "07500000000", "password": "staff1234"}).json["token"]
    r = client.post("/auth/signup", json={**body, "email_verification_token": staff})   # a login is not a step
    assert r.status_code == 401
    app.config["STEP_TOKEN_MINUTES"] = -1
    stale = form(api, email="late@example.com", phone="07701234568")
    assert client.post("/auth/signup", json=stale).json["error"] == "email_not_verified"
    assert count("users") == 1                                   # only staff


def test_one_account_per_mailbox_and_per_phone(client, api):
    body = form(api)
    assert client.post("/auth/signup", json=body).status_code == 201
    again = client.post("/auth/signup", json={**body, "phone": "07701234599"})      # same code, new phone
    assert again.status_code == 409 and again.json["error"] == "email_taken"
    other_spelling = form(api, email="RAND+second@example.com", phone="07701234598")
    assert client.post("/auth/signup", json=other_spelling).status_code == 201       # example.com: + is a new box
    gmail = form(api, email="ra.nd@gmail.com", phone="07701234597")
    assert client.post("/auth/signup", json=gmail).status_code == 201
    sql("UPDATE otp_codes SET created_at = created_at - interval '2 minutes'")   # past the resend wait
    dots = form(api, email="rand+x@googlemail.com", phone="07701234596")
    assert client.post("/auth/signup", json=dots).json["error"] == "email_taken"     # the same Gmail box
    phone = client.post("/auth/signup", json=form(api, email="new@example.com", phone="0770 123 4567"))
    assert phone.status_code == 409 and phone.json["error"] == "phone_taken"


def test_a_taken_phone_leaves_no_places_behind(client, api):
    client.post("/auth/signup", json=form(api))
    r = client.post("/auth/signup", json=form(api, email="b@example.com", household=HOME, business=SHOP))
    assert r.json["error"] == "phone_taken"
    assert count("places") == 0 and count("place_reviews") == 0 and count("users") == 2


def test_offline_rehearsal_signs_up_without_an_email(client, app):
    app.config["OTP_REQUIRED"] = False
    r = client.post("/auth/signup", json={"name": "ڕەند", "phone": "07701234567", "password": "secret123",
                                          "household": HOME})
    assert r.status_code == 201 and r.json["user"]["email"] is None
    me = client.get("/me", headers=bearer(r)).json
    assert me["email_verified"] is False and me["places"][0]["kind"] == "household"
    bad = client.post("/auth/signup", json={"name": "x", "phone": "07701234568", "password": "secret123",
                                            "email_verification_token": "garbage"})
    assert bad.status_code == 401                               # a token that is sent must still be good


# ---------------------------------------------------------------- what the form may contain

FORMS = itertools.count(1)


def errors_for(client, api, **extra):
    n = next(FORMS)
    r = client.post("/auth/signup", json=form(api, email=f"f{n}@example.com", phone=f"0770123{n:04d}", **extra))
    assert r.status_code == 400 and r.json["error"] == "invalid_profile", r.json
    assert r.json["message"] != "invalid_profile"
    return r.json["fields"]


def test_field_problems_are_named(client, api):
    assert errors_for(client, api, household={**HOME, "name": " "}) == {"household.name": "required"}
    assert errors_for(client, api, household={**HOME, "name": "x"}) == {"household.name": "too_short"}
    assert errors_for(client, api, business={**SHOP, "name": "x" * 121}) == {"business.name": "too_long"}
    for bad in (0, 31, "4", 4.0, True):
        assert errors_for(client, api, household={**HOME, "residents_count": bad}) == \
            {"household.residents_count": "invalid"}, bad
    assert errors_for(client, api, household={k: v for k, v in HOME.items() if k != "residents_count"}) == \
        {"household.residents_count": "required"}
    assert errors_for(client, api, business={**SHOP, "category": "bank"}) == {"business.category": "invalid"}
    assert errors_for(client, api, business={**SHOP, "license_number": "x" * 65}) == \
        {"business.license_number": "too_long"}
    assert errors_for(client, api, business={**SHOP, "lat": None}) == {"business.location": "required"}
    assert errors_for(client, api, business={**SHOP, "lat": "35.5"}) == {"business.location": "invalid"}
    assert errors_for(client, api, business={**SHOP, "lat": 37.33, "lon": -122.03}) == \
        {"business.location": "outside_service_area"}               # the iOS simulator's Cupertino
    assert errors_for(client, api, household={**HOME, "neighbourhood_id": 999}) == \
        {"household.neighbourhood_id": "unknown"}
    assert errors_for(client, api, neighbourhood_id=999) == {"neighbourhood_id": "unknown"}
    assert errors_for(client, api, household="my house") == {"household": "invalid"}
    assert errors_for(client, api, name="x" * 81) == {"name": "too_long"}


def test_a_household_sent_as_a_business_is_refused(client, api):
    assert errors_for(client, api, business=HOME) == {"business.residents_count": "unknown_field",
                                                      "business.category": "required"}
    assert errors_for(client, api, household={**HOME, "owner_id": 1, "verification_status": "verified"}) == \
        {"household.owner_id": "unknown_field", "household.verification_status": "unknown_field"}


def test_a_refused_form_writes_nothing(client, api):
    errors_for(client, api, household=HOME, business={**SHOP, "category": "bank"})
    assert count("users") == 1 and count("places") == 0


# ---------------------------------------------------------------- logging in

def test_log_in_with_the_email_in_any_spelling_or_with_the_phone(client, api):
    client.post("/auth/signup", json=form(api, email="Ra.Nd+app@Gmail.com"))
    for who in ("ra.nd+app@gmail.com", "RAND@gmail.com", "rand@googlemail.com", "07701234567", "+9647701234567"):
        r = client.post("/auth/login", json={"login": who, "password": "secret123"})
        assert r.status_code == 200, who
    assert client.post("/auth/login", json={"email": "rand@gmail.com", "password": "secret123"}).status_code == 200
    for who, password in (("rand@gmail.com", "wrong!!"), ("nobody@gmail.com", "secret123"), ("@", "secret123")):
        r = client.post("/auth/login", json={"login": who, "password": password})
        assert r.status_code == 401 and r.json["error"] == "bad_login"


def test_an_account_without_a_password_cannot_log_in_with_one(client, api):
    client.post("/auth/signup", json=form(api))
    sql("UPDATE users SET password_hash = NULL WHERE email = 'rand@example.com'")     # Google-only
    for password in ("secret123", "", None):
        assert client.post("/auth/login", json={"login": "rand@example.com", "password": password}).status_code == 401


# ---------------------------------------------------------------- changing a place

def test_adding_and_changing_a_place_later(client, api):
    me = bearer(client.post("/auth/signup", json=form(api)))
    added = client.post("/me/places", json={"kind": "household", **HOME}, headers=me)
    assert added.status_code == 201 and added.json["verification_status"] == "pending"
    place_id = added.json["id"]
    sql("UPDATE places SET verification_status = 'verified', verified_at = now() WHERE id = %s", (place_id,))

    # the address is not what staff checked: still verified
    r = client.post("/me/places", json={"kind": "household", **HOME, "address": "کۆڵانی ٤"}, headers=me)
    assert r.status_code == 200 and r.json["verification_status"] == "verified" and r.json["address"] == "کۆڵانی ٤"
    # the same pin sent back after a round trip through JSON is not a move
    r = client.post("/me/places", json={"kind": "household", **HOME, "lat": r.json["lat"], "lon": r.json["lon"]},
                    headers=me)
    assert r.json["verification_status"] == "verified"
    # more people at home: back to the queue
    r = client.post("/me/places", json={"kind": "household", **HOME, "residents_count": 6}, headers=me)
    assert r.json["verification_status"] == "pending" and r.json["verified_at"] is None
    assert sql("SELECT status FROM place_reviews WHERE place_id = %s ORDER BY id", (place_id,)) == \
        [("pending",), ("pending",)]
    assert count("places") == 1


def test_moving_a_business_or_resubmitting_a_rejected_one(client, api):
    me = bearer(client.post("/auth/signup", json=form(api, business=SHOP)))
    sql("""UPDATE places SET verification_status = 'verified', verified_at = now()""")
    r = client.post("/me/places", json={"kind": "business", **SHOP, "lat": SHOP["lat"] + 0.001}, headers=me)
    assert r.json["verification_status"] == "pending"
    sql("""UPDATE places SET verification_status = 'rejected', rejection_reason = 'مۆڵەتەکە ناخوێندرێتەوە'""")
    r = client.post("/me/places", json={"kind": "business", **SHOP, "address": "بازاڕ"}, headers=me)
    assert r.json["verification_status"] == "pending" and r.json["rejection_reason"] is None


def test_changing_a_place_checks_it_like_signing_up(client, api):
    me = bearer(client.post("/auth/signup", json=form(api)))
    r = client.post("/me/places", json={"kind": "shop", **SHOP}, headers=me)
    assert r.status_code == 400 and r.json["fields"] == {"kind": "invalid"}
    r = client.post("/me/places", json={"kind": "business", **SHOP, "category": None}, headers=me)
    assert r.json["fields"] == {"business.category": "required"}
    assert client.post("/me/places", json={"kind": "business", **SHOP}).status_code == 401
    assert count("places") == 0


def test_two_taps_add_one_place(app, api):
    from test_races import at_once
    me = bearer(app.test_client().post("/auth/signup", json=form(api)))
    statuses = at_once(4, lambda i: app.test_client().post("/me/places", json={"kind": "business", **SHOP},
                                                           headers=me).status_code)
    assert sorted(statuses) == [200, 200, 200, 201] and count("places") == 1


# ---------------------------------------------------------------- money and privacy

def test_the_money_staff_credited_shows_on_the_account_page(client, api):
    me = bearer(client.post("/auth/signup", json=form(api, household=HOME, business=SHOP)))
    sql("""INSERT INTO place_payments (place_id, month, amount_iqd)
           SELECT id, DATE '2026-09-01', CASE kind WHEN 'household' THEN 10000 ELSE 25000 END FROM places""")
    sql("INSERT INTO place_payments (place_id, month, amount_iqd) SELECT id, DATE '2026-10-01', 10000 "
        "FROM places WHERE kind = 'household'")
    money = client.get("/me", headers=me).json["money"]
    assert money["total_iqd"] == 45000
    assert [(p["month"], p["kind"], p["amount_iqd"]) for p in money["payments"]] == [
        ("2026-10-01", "household", 10000), ("2026-09-01", "household", 10000), ("2026-09-01", "business", 25000)]


def test_a_home_location_appears_in_no_public_answer(client, api):
    owner = bearer(client.post("/auth/signup", json=form(api, household=HOME, business=SHOP)))
    neighbour = api.signup()
    dirty_spot(api, seed=7)                                   # a report, so /reports has something in it
    report_id = sql("SELECT id FROM reports ORDER BY id LIMIT 1")[0][0]
    secrets_ = [f"{HOME['lat']:.6f}", f"{HOME['lon']:.6f}", f"{HOME['lat']:.4f}", f"{HOME['lon']:.4f}",
                HOME["address"], HOME["name"], SHOP["name"]]
    for path in ("/leaderboard", "/reports", f"/reports/{report_id}", "/pins", "/notifications", "/bins",
                 "/neighbourhoods", "/neighbourhoods?geo=1", "/me", "/tasks", "/rewards"):
        r = client.get(path, headers=neighbour)
        assert r.status_code == 200, path
        text = r.get_data(as_text=True)
        assert not any(s in text for s in secrets_), path
    # its owner does see it
    assert f"{HOME['lat']}" in client.get("/me", headers=owner).get_data(as_text=True)
