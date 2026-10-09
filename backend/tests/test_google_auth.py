"""Sign in with Google (app/google_auth.py). The verifier is tested for real, with tokens signed by a key
made here and a stand-in for Google's key endpoint; the endpoints use FakeGoogleVerifier. No test
talks to Google."""
import time

import psycopg
import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import crypt
from google.auth import jwt as google_jwt

from app import auth
from app.google_auth import (REFETCH_SECONDS, STALE_SECONDS, FakeGoogleVerifier, GoogleEmailUnverified,
                             GoogleTokenInvalid, GoogleUnavailable, GoogleVerifier)
from conftest import STAFF, TEST_DB
from test_races import at_once

WEB, ANDROID = "web-client.apps.googleusercontent.com", "android-client.apps.googleusercontent.com"
HOME = {"name": "ماڵی شنە", "residents_count": 3, "lat": 35.5701, "lon": 45.4202}


def sql(statement, params=()):
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else None


# ---------------------------------------------------------------- the verifier, with real signatures

def new_key(kid):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.PEM,
                                           serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return crypt.RSASigner.from_string(private, key_id=kid), public


@pytest.fixture(scope="module")
def keys():
    return {"k1": new_key("k1"), "k2": new_key("k2"), "impostor": new_key("k1")}


def sign(keys, name="k1", **changes):
    now = int(time.time())
    claims = {"iss": "https://accounts.google.com", "aud": WEB, "sub": "110169484474386276334",
              "email": "Shna.Ali@gmail.com", "email_verified": True, "name": "Shna", "iat": now, "exp": now + 3600}
    claims.update(changes)
    return google_jwt.encode(keys[name][0], {k: v for k, v in claims.items() if v is not None}).decode()


class KeyEndpoint:
    """Stands in for requests.get on Google's key URL: counts calls, can be down or answer badly."""

    def __init__(self, keys, *names, max_age=3600):
        self.keys, self.names, self.max_age = keys, list(names), max_age
        self.calls, self.down, self.status = 0, False, 200

    def __call__(self, url, timeout):
        self.calls += 1
        if self.down:
            raise requests.ConnectionError("no route to Google")
        answer = type("Answer", (), {})()
        answer.status_code, answer.headers = self.status, {"Cache-Control": f"public, max-age={self.max_age}"}
        answer.json = lambda: {name: self.keys[name][1] for name in self.names}
        return answer


def verifier(endpoint, now):
    return GoogleVerifier([WEB, ANDROID], http_get=endpoint, clock=lambda: now[0])


def test_a_real_google_token_is_accepted(keys):
    v = verifier(KeyEndpoint(keys, "k1"), [1000.0])
    assert v.verify(sign(keys)) == {"sub": "110169484474386276334", "email": "Shna.Ali@gmail.com", "name": "Shna"}
    assert v.verify(sign(keys, aud=ANDROID, iss="accounts.google.com", email_verified="true"))["sub"]
    now = int(time.time())
    assert v.verify(sign(keys, exp=now - 5, iat=now - 3600))          # within the 10 s of clock slack


def test_what_is_refused(keys):
    v = verifier(KeyEndpoint(keys, "k1"), [1000.0])
    now = int(time.time())
    for bad in (sign(keys, aud="someone-elses-app"), sign(keys, iss="https://evil.example.com"),
                sign(keys, exp=now - 30, iat=now - 3600), sign(keys, sub=None),
                sign(keys, "impostor"),                     # right key id, wrong key: a forged signature
                "not.a.token", "", None):
        with pytest.raises(GoogleTokenInvalid):
            v.verify(bad)
    for unverified in (sign(keys, email_verified=False), sign(keys, email_verified=None), sign(keys, email=None)):
        with pytest.raises(GoogleEmailUnverified):
            v.verify(unverified)


def test_keys_are_cached_as_long_as_google_says(keys):
    endpoint, now = KeyEndpoint(keys, "k1", max_age=600), [1000.0]
    v = verifier(endpoint, now)
    v.verify(sign(keys))
    v.verify(sign(keys))
    assert endpoint.calls == 1
    now[0] += 601
    v.verify(sign(keys))
    assert endpoint.calls == 2


def test_a_flaky_hotspot_uses_yesterdays_keys_but_not_older(keys):
    endpoint, now = KeyEndpoint(keys, "k1", max_age=600), [1000.0]
    v = verifier(endpoint, now)
    v.verify(sign(keys))
    endpoint.down = True
    now[0] += 3600                                   # stale, and Google cannot be reached
    assert v.verify(sign(keys))["sub"]
    now[0] += STALE_SECONDS
    with pytest.raises(GoogleUnavailable):
        v.verify(sign(keys))


def test_no_keys_at_all_is_unavailable_not_invalid(keys):
    endpoint = KeyEndpoint(keys, "k1")
    endpoint.down = True
    with pytest.raises(GoogleUnavailable):
        verifier(endpoint, [1000.0]).verify(sign(keys))
    endpoint.down, endpoint.status = False, 500      # an error page instead of keys
    with pytest.raises(GoogleUnavailable):
        verifier(endpoint, [1000.0]).verify(sign(keys))


def test_a_rotated_key_is_fetched_but_not_on_every_request(keys):
    endpoint, now = KeyEndpoint(keys, "k1"), [1000.0]
    v = verifier(endpoint, now)
    v.verify(sign(keys))
    endpoint.names = ["k1", "k2"]                    # Google starts signing with a new key
    with pytest.raises(GoogleTokenInvalid):
        v.verify(sign(keys, "k2"))                   # just fetched: no second fetch for an unknown key id
    assert endpoint.calls == 1
    now[0] += REFETCH_SECONDS + 1
    assert v.verify(sign(keys, "k2"))["sub"]
    assert endpoint.calls == 2


# ---------------------------------------------------------------- the endpoints

NEW = {"sub": "g-new", "email": "Shna.Ali@gmail.com", "name": "شنە"}


@pytest.fixture()
def google(app):
    app.google_verifier = FakeGoogleVerifier({
        "new": NEW, "other": {"sub": "g-other", "email": "other@gmail.com", "name": "Other"},
        "bad": GoogleTokenInvalid(), "unverified": GoogleEmailUnverified(), "down": GoogleUnavailable("offline")})
    return app.google_verifier


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def start(client, id_token="new"):
    r = client.post("/auth/google", json={"id_token": id_token})
    assert r.status_code == 200 and r.json["status"] == "registration_required", r.json
    return r.json["google_signup_token"]


def register(client, token, phone="07701234567", **extra):
    return client.post("/auth/google/register", json={"google_signup_token": token, "phone": phone, **extra})


def password_account(client, app, email="shna.ali@gmail.com", phone="07709876543"):
    """An account made the usual way: email code, then a password."""
    from conftest import Api
    r = client.post("/auth/signup", json={"name": "شنە", "phone": phone, "password": "secret123",
                                          "email_verification_token": Api(client).email_token(email)})
    assert r.status_code == 201, r.json
    return r.json["user"]["id"]


def test_google_off_until_configured(client):
    for path in ("/auth/google", "/auth/google/register", "/auth/google/link"):
        r = client.post(path, json={})
        assert r.status_code == 404 and r.json["error"] == "google_disabled", path
    assert client.get("/auth/config").json["google"] == {"enabled": False, "server_client_id": None}


def test_what_google_says_becomes_the_right_answer(client, google):
    for token, status, code in (("bad", 401, "google_token_invalid"), ("unverified", 403, "google_email_unverified"),
                                ("down", 503, "google_unavailable"), (None, 401, "google_token_invalid")):
        r = client.post("/auth/google", json={"id_token": token})
        assert (r.status_code, r.json["error"]) == (status, code)
        assert r.json["message"] != code


def test_a_new_google_account_makes_nothing_until_it_registers(client, google, app):
    r = client.post("/auth/google", json={"id_token": "new"})
    assert r.json["profile"] == {"name": "شنە", "email": "shna.ali@gmail.com"} and r.json["email_has_account"] is False
    assert sql("SELECT count(*) FROM users") == [(1,)] and sql("SELECT count(*) FROM user_identities") == [(0,)]
    with app.app_context():
        claims = auth.read_step_token(r.json["google_signup_token"], auth.GOOGLE_SIGNUP)
        assert claims["google_sub"] == "g-new" and claims["email_key"] == "shnaali@gmail.com"
        assert auth.read_step_token(r.json["google_signup_token"], auth.EMAIL_VERIFIED) is None
    # and it is no email code either: /auth/signup refuses it
    assert client.post("/auth/signup", json={"name": "x", "phone": "07701234567", "password": "secret123",
                                             "email_verification_token": r.json["google_signup_token"]}).status_code == 401


def test_register_then_sign_in_with_one_tap(client, google):
    r = register(client, start(client), household=HOME)
    assert r.status_code == 201, r.json
    me = client.get("/me", headers=bearer(r.json["token"])).json
    assert (me["name"], me["email"], me["email_verified"], me["auth_methods"]) == \
        ("شنە", "shna.ali@gmail.com", True, ["google"])
    assert me["places"][0]["kind"] == "household" and me["places"][0]["verification_status"] == "pending"

    sql("UPDATE user_identities SET last_login_at = now() - interval '1 day'")
    again = client.post("/auth/google", json={"id_token": "new"})
    assert again.json["status"] == "signed_in" and again.json["user"]["id"] == r.json["user"]["id"]
    assert sql("SELECT last_login_at > now() - interval '1 minute' FROM user_identities") == [(True,)]
    # no password: the password login cannot open it
    assert client.post("/auth/login", json={"login": "shna.ali@gmail.com", "password": ""}).status_code == 401


def test_register_checks_the_form(client, google, app):
    token = start(client)
    assert register(client, token, phone="").json["error"] == "missing_fields"
    assert register(client, token, phone="0750").json["error"] == "invalid_phone"
    assert register(client, token, household={**HOME, "residents_count": 0}).json["fields"] == \
        {"household.residents_count": "invalid"}
    assert register(client, token, name="رەند").json["user"]["name"] == "رەند"     # the form's name wins
    for stale in ("garbage", None):
        r = register(client, stale)
        assert r.status_code == 401 and r.json["error"] == "google_signup_expired"
    app.config["STEP_TOKEN_MINUTES"] = -1
    assert register(client, start(client, "other"), phone="07701234560").json["error"] == "google_signup_expired"


def test_the_same_google_account_registers_once(client, google, app):
    token = start(client)
    assert register(client, token).status_code == 201
    again = register(client, token, phone="07701234560")
    assert again.status_code == 409 and again.json["error"] == "google_already_linked"
    # two taps on "create account" at the same moment
    other = start(client, "other")
    results = at_once(3, lambda i: register(app.test_client(), other, phone="07701234561").status_code)
    assert sorted(results) == [201, 409, 409]
    assert sql("SELECT count(*) FROM user_identities WHERE subject = 'g-other'") == [(1,)]


def test_an_email_with_a_password_account_is_offered_a_link(client, google, app):
    old_id = password_account(client, app)
    sql("INSERT INTO point_ledger (user_id, amount, kind, status) VALUES (%s, 40, 'cleanup', 'released')", (old_id,))
    r = client.post("/auth/google", json={"id_token": "new"})
    assert r.json["email_has_account"] is True
    taken = register(client, r.json["google_signup_token"])
    assert taken.status_code == 409 and taken.json["error"] == "email_taken" and taken.json["can_link"] is True

    link = {"google_signup_token": r.json["google_signup_token"], "login": "shna.ali@gmail.com"}
    wrong = client.post("/auth/google/link", json={**link, "password": "guess123"})
    assert wrong.status_code == 401 and wrong.json["error"] == "bad_login"
    ok = client.post("/auth/google/link", json={**link, "password": "secret123"})
    assert ok.status_code == 200 and ok.json["user"]["id"] == old_id
    me = client.get("/me", headers=bearer(ok.json["token"])).json
    assert me["released"] == 40 and me["auth_methods"] == ["password", "google"]
    signed_in = client.post("/auth/google", json={"id_token": "new"}).json
    assert signed_in["status"] == "signed_in" and signed_in["user"]["id"] == old_id
    assert client.post("/auth/login", json={"login": "07709876543", "password": "secret123"}).status_code == 200
    assert sql("SELECT count(*) FROM users") == [(2,)]


def test_a_phone_with_an_account_is_offered_a_link_too(client, google, app):
    password_account(client, app, email="someone@example.com", phone="07701234567")
    taken = register(client, start(client))
    assert taken.json["error"] == "phone_taken" and taken.json["can_link"] is True


def test_an_account_from_before_emails_gets_googles_email_when_linked(client, google, app):
    app.config["OTP_REQUIRED"] = False
    old = client.post("/auth/signup", json={"name": "کاوە", "phone": "07701112222", "password": "secret123"})
    ok = client.post("/auth/google/link", json={"google_signup_token": start(client), "login": "0770 111 2222",
                                                "password": "secret123"})
    assert ok.status_code == 200 and ok.json["user"]["id"] == old.json["user"]["id"]
    assert ok.json["user"]["email"] == "shna.ali@gmail.com"
    assert sql("SELECT email_key, email_verified_at IS NOT NULL FROM users WHERE id = %s",
               (old.json["user"]["id"],)) == [("shnaali@gmail.com", True)]


def test_linking_keeps_the_email_when_another_account_has_it(client, google, app):
    password_account(client, app)                                        # owns shna.ali@gmail.com
    app.config["OTP_REQUIRED"] = False
    old = client.post("/auth/signup", json={"name": "کاوە", "phone": "07701112222", "password": "secret123"})
    ok = client.post("/auth/google/link", json={"google_signup_token": start(client), "login": "07701112222",
                                                "password": "secret123"})
    assert ok.status_code == 200 and ok.json["user"]["email"] is None
    assert client.post("/auth/google", json={"id_token": "new"}).json["user"]["id"] == old.json["user"]["id"]


def test_what_cannot_be_linked(client, google, app):
    password_account(client, app)
    first = client.post("/auth/google/link", json={"google_signup_token": start(client), "login": "shna.ali@gmail.com",
                                                   "password": "secret123"})
    assert first.status_code == 200
    # a second Google account for the same person
    second = client.post("/auth/google/link", json={"google_signup_token": start(client, "other"),
                                                    "login": "shna.ali@gmail.com", "password": "secret123"})
    assert second.status_code == 409 and second.json["error"] == "google_already_linked"
    # the dashboard account stays behind its own password
    staff = client.post("/auth/google/link", json={"google_signup_token": start(client, "other"),
                                                   "login": STAFF[0], "password": STAFF[1]})
    assert staff.status_code == 403
    expired = client.post("/auth/google/link", json={"google_signup_token": "old", "login": "shna.ali@gmail.com",
                                                     "password": "secret123"})
    assert expired.status_code == 401 and expired.json["error"] == "google_signup_expired"


def test_auth_config_tells_the_app_what_it_needs_and_nothing_secret(client, google, app):
    app.config.update(SECRET_KEY="secret-key-marker-0123456789abcdef", OTP_PEPPER="pepper-marker",
                      SMTP_PASSWORD="smtp-password-marker", GOOGLE_SERVER_CLIENT_ID=WEB)
    r = client.get("/auth/config")
    body = r.get_data(as_text=True)
    assert r.json["google"] == {"enabled": True, "server_client_id": WEB}
    assert r.json["otp"] == {"required": True, "length": 6, "ttl_seconds": 300, "resend_seconds": 60}
    assert r.json["place_kinds"] == ["household", "business"]
    assert {"code": "cafe", "name": "کافێ"} in r.json["business_categories"]
    assert r.json["service_area"] == [34.3, 44.3, 36.6, 46.4] and len(r.json["map_center"]) == 2
    assert not any(marker in body for marker in ("secret-key-marker", "pepper-marker", "smtp-password-marker"))
