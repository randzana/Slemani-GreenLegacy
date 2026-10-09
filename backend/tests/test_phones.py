"""Phones in one form (app/phones.py): one number written several ways is one account and one login."""
from app import phones
from conftest import STAFF


def test_every_way_of_writing_an_iraqi_mobile_is_one_number(app):
    with app.app_context():
        for typed in ("07501234567", "0750 123 4567", "(0750) 123-4567", "+9647501234567", "9647501234567",
                      "009647501234567", "7501234567"):
            assert phones.normalise(typed) == ("+9647501234567", None), typed


def test_not_a_number_or_another_country(app):
    with app.app_context():
        for typed in ("", None, "abc", "0750", "07012345678"):    # 070 is no Iraqi mobile network
            assert phones.normalise(typed) == (None, "invalid_phone"), typed
        assert phones.normalise("+14155550123") == (None, "phone_not_allowed")
        assert phones.normalise("0533123456") == ("+964533123456", None)     # a Slemani landline: no SMS needed
    app.config["PHONE_ALLOWED_COUNTRY_CODES"] = ("964", "1")
    with app.app_context():
        assert phones.normalise("+14155550123") == ("+14155550123", None)


def test_login_finds_the_staff_account_however_the_number_is_typed(client):
    for typed in (STAFF[0], "0750 000 0000", "+9647500000000", "9647500000000"):
        r = client.post("/auth/login", json={"phone": typed, "password": STAFF[1]})
        assert r.status_code == 200, typed
        assert r.json["user"]["phone"] == "+9647500000000"
    assert client.post("/auth/login", json={"phone": STAFF[0], "password": "nope"}).status_code == 401
    assert client.post("/auth/login", json={"phone": "garbage", "password": STAFF[1]}).status_code == 401
    assert client.post("/auth/login", json={}).status_code == 401


def test_signup_stores_the_normalised_number_and_refuses_bad_ones(client, app):
    app.config["OTP_REQUIRED"] = False          # the phone rules are the same with or without an email
    r = client.post("/auth/signup", json={"name": "ڕەند", "phone": "0770 123 4567", "password": "secret123"})
    assert r.status_code == 201 and r.json["user"]["phone"] == "+9647701234567"
    again = client.post("/auth/signup", json={"name": "x", "phone": "+9647701234567", "password": "secret123"})
    assert again.status_code == 409 and again.json["error"] == "phone_taken"
    bad = client.post("/auth/signup", json={"name": "x", "phone": "0750", "password": "secret123"})
    assert bad.status_code == 400 and bad.json["error"] == "invalid_phone" and bad.json["message"] != "invalid_phone"
    abroad = client.post("/auth/signup", json={"name": "x", "phone": "+14155550123", "password": "secret123"})
    assert abroad.status_code == 400 and abroad.json["error"] == "phone_not_allowed"
