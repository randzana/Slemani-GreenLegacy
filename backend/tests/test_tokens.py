"""Which token opens what: only an access token is a login, and a step token only opens its own step.
One SECRET_KEY signs every kind, so this is the only thing keeping them apart."""
import datetime as dt

import jwt

from app import auth
from conftest import STAFF

STAFF_ID = 1          # seed.py's staff account is the first row


def now():
    return dt.datetime.now(dt.timezone.utc)


def sign(app, payload, key=None):
    return jwt.encode(payload, key or app.config["SECRET_KEY"], algorithm="HS256")


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def step_token(app, typ, **claims):
    with app.app_context():
        return auth.make_step_token(typ, **claims)


def read_step(app, token, typ):
    with app.app_context():
        return auth.read_step_token(token, typ)


def test_login_tokens_say_they_are_access_tokens(client, app):
    token = client.post("/auth/login", json={"phone": STAFF[0], "password": STAFF[1]}).json["token"]
    assert jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["typ"] == "access"
    assert client.get("/me", headers=bearer(token)).status_code == 200


def test_a_step_token_never_opens_the_api(client, app):
    for token in (step_token(app, "email_verified", email="a@example.com", email_key="a@example.com"),
                  step_token(app, "google_signup", google_sub="110169484474386276334", email="a@gmail.com"),
                  # even one that carries a real user id as its subject
                  step_token(app, "email_verified", sub=str(STAFF_ID))):
        r = client.get("/me", headers=bearer(token))
        assert r.status_code == 401 and r.json["error"] == "unauthorized"


def test_the_typ_alone_keeps_a_step_token_out(client, app):
    """Without its audience, a step token's typ is still enough for login_required to refuse it."""
    for typ in ("email_verified", "google_signup", "refresh", ""):
        token = sign(app, {"typ": typ, "sub": str(STAFF_ID), "iat": now(), "exp": now() + dt.timedelta(hours=1)})
        assert client.get("/me", headers=bearer(token)).status_code == 401, typ


def test_a_login_token_is_not_a_step_token(client, app):
    login = client.post("/auth/login", json={"phone": STAFF[0], "password": STAFF[1]}).json["token"]
    assert read_step(app, login, "email_verified") is None
    assert read_step(app, login, "google_signup") is None

    email = step_token(app, "email_verified", email="a@example.com", email_key="a@example.com")
    assert read_step(app, email, "google_signup") is None          # each step accepts only its own kind
    claims = read_step(app, email, "email_verified")
    assert claims["email"] == "a@example.com" and claims["aud"] == "gl-step"


def test_step_tokens_expire_and_belong_to_this_server(app):
    app.config["STEP_TOKEN_MINUTES"] = -1
    expired = step_token(app, "email_verified", email="a@example.com")
    assert read_step(app, expired, "email_verified") is None
    app.config["STEP_TOKEN_MINUTES"] = 10
    forged = sign(app, {"typ": "email_verified", "aud": "gl-step", "email": "a@example.com",
                        "exp": now() + dt.timedelta(minutes=5)}, key="someone-elses-secret-key-of-32-bytes!")
    assert read_step(app, forged, "email_verified") is None
    for junk in (None, "", "not.a.token", 42):
        assert read_step(app, junk, "email_verified") is None
    # a hand-made token without an expiry is refused too
    no_exp = sign(app, {"typ": "email_verified", "aud": "gl-step", "email": "a@example.com"})
    assert read_step(app, no_exp, "email_verified") is None


def test_tokens_from_before_typ_still_log_in(client, app):
    legacy = sign(app, {"sub": str(STAFF_ID), "role": "staff", "iat": now(), "exp": now() + dt.timedelta(days=7)})
    r = client.get("/me", headers=bearer(legacy))
    assert r.status_code == 200 and r.json["role"] == "staff"


def test_a_broken_subject_is_refused_not_a_server_error(client, app):
    later = now() + dt.timedelta(hours=1)
    for payload in ({"iat": now(), "exp": later},                                   # no subject
                    {"sub": "abc", "iat": now(), "exp": later},
                    {"sub": "110169484474386276334", "iat": now(), "exp": later},  # a Google sub, too big
                    {"sub": "0", "iat": now(), "exp": later},
                    {"sub": "-1", "iat": now(), "exp": later}):
        r = client.get("/me", headers=bearer(sign(app, payload)))
        assert r.status_code == 401 and r.json["error"] == "unauthorized", payload
