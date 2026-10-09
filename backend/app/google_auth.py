"""Sign in with Google: who a person is, as Google vouches for it.

The phone sends only the ID token Google gave it. Everything we use (the stable subject, the email,
whether Google verified that email, the name) is read from that token after it is checked here:
- signed by one of Google's current keys. The keys are fetched from CERTS_URL and kept as long as
  Google's Cache-Control allows; if a refresh fails the old keys serve for up to a day, so a flaky
  hotspot does not stop every sign-in, and with no keys at all it is 503 google_unavailable;
- issued by accounts.google.com, for one of our GOOGLE_CLIENT_IDS, not expired (10 s clock slack);
- with email_verified true. Google has then proved the email, so no email code is needed.
Accounts are keyed on Google's "sub", never on the email (emails change hands). No Google access
or refresh token is asked for or kept: we only need to know who the person is.

The verifier is injected through create_app like the detector; tests use FakeGoogleVerifier.
"""
import logging
import re
import threading
import time

import jwt as pyjwt
import psycopg
import requests
from flask import Blueprint, current_app, jsonify
from google.auth import exceptions as google_errors
from google.auth import jwt as google_jwt

from . import accounts, emails, phones
from .auth import (GOOGLE_SIGNUP, error, json_body, make_step_token, make_token, password_user, public_user,
                   read_step_token)
from .db import query, savepoint

log = logging.getLogger(__name__)
bp = Blueprint("google", __name__)

CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"
ISSUERS = ("accounts.google.com", "https://accounts.google.com")
SKEW_SECONDS = 10
STALE_SECONDS = 24 * 3600      # how long old keys still serve when Google cannot be reached
REFETCH_SECONDS = 60           # an unknown key id fetches again at most this often (no fetch storms)


class GoogleTokenInvalid(Exception):
    """Not a token Google made for us, or no longer valid."""


class GoogleEmailUnverified(Exception):
    """Google has not verified the account's email."""


class GoogleUnavailable(Exception):
    """Google's keys cannot be fetched and none are cached."""


def _max_age(cache_control):
    found = re.search(r"max-age=(\d+)", cache_control or "")
    return int(found.group(1)) if found else 3600


class GoogleVerifier:
    def __init__(self, client_ids, certs_url=CERTS_URL, http_get=None, clock=time.time, timeout=5):
        self.client_ids = list(client_ids)
        self.certs_url, self.http_get, self.clock, self.timeout = certs_url, http_get or requests.get, clock, timeout
        self._certs, self._fetched_at, self._fresh_until = None, 0.0, 0.0
        self._lock = threading.Lock()      # one fetch at a time; the others wait for its keys

    def _keys(self, kid=None):
        with self._lock:
            now = self.clock()
            fresh = self._certs and now < self._fresh_until
            # a key id we do not know: Google may have rotated its keys since we fetched them
            rotated = self._certs and kid and kid not in self._certs and now - self._fetched_at > REFETCH_SECONDS
            if fresh and not rotated:
                return self._certs
            try:
                r = self.http_get(self.certs_url, timeout=self.timeout)
                if r.status_code != 200:
                    raise ValueError(f"HTTP {r.status_code}")
                certs = r.json()
                if not isinstance(certs, dict) or not certs:
                    raise ValueError("no keys in the answer")
            except Exception as exc:      # no network, a timeout, an HTML error page...
                if self._certs and now - self._fetched_at < STALE_SECONDS:
                    log.warning("Google keys not refreshed (%s): using the ones from %.0f s ago",
                                type(exc).__name__, now - self._fetched_at)
                    return self._certs
                raise GoogleUnavailable(type(exc).__name__) from exc
            self._certs, self._fetched_at = certs, now
            self._fresh_until = now + _max_age(r.headers.get("Cache-Control"))
            return certs

    def verify(self, id_token):
        """{sub, email, name} from a valid Google ID token, else one of the three errors above."""
        token = str(id_token or "")
        try:
            kid = pyjwt.get_unverified_header(token).get("kid")
        except pyjwt.PyJWTError as exc:
            raise GoogleTokenInvalid("not a JWT") from exc
        certs = self._keys(kid)
        try:
            claims = google_jwt.decode(token, certs=certs, audience=self.client_ids,
                                       clock_skew_in_seconds=SKEW_SECONDS)
        except (ValueError, google_errors.GoogleAuthError) as exc:
            raise GoogleTokenInvalid(type(exc).__name__) from exc
        if claims.get("iss") not in ISSUERS or not claims.get("sub"):
            raise GoogleTokenInvalid("wrong issuer or no subject")
        if claims.get("email_verified") not in (True, "true") or not claims.get("email"):
            raise GoogleEmailUnverified()
        return {"sub": str(claims["sub"]), "email": claims["email"], "name": claims.get("name") or ""}


class FakeGoogleVerifier:
    """For tests: test token strings mapped to the claims verify() returns, or to the error it raises."""

    def __init__(self, tokens=None):
        self.tokens = dict(tokens or {})

    def verify(self, id_token):
        found = self.tokens.get(id_token)
        if found is None:
            raise GoogleTokenInvalid("unknown test token")
        if isinstance(found, Exception):
            raise found
        return dict(found)


def make_google_verifier(cfg):
    """None (Google sign-in off, the app hides its button) until GOOGLE_CLIENT_IDS is set."""
    return GoogleVerifier(cfg["GOOGLE_CLIENT_IDS"]) if cfg["GOOGLE_CLIENT_IDS"] else None


# ---------------------------------------------------------------- endpoints

def _from_google(id_token):
    """(who Google says this is, None) or (None, the error to answer)."""
    try:
        google = current_app.google_verifier.verify(id_token)
    except GoogleEmailUnverified:
        return None, error("google_email_unverified", 403)
    except GoogleUnavailable as exc:
        log.warning("Google sign-in unavailable: %s", exc)
        return None, error("google_unavailable", 503)
    except GoogleTokenInvalid:
        return None, error("google_token_invalid", 401)
    email, key, problem = emails.normalise(google["email"])
    if problem:
        return None, error("google_token_invalid", 401)
    return {**google, "email": email, "email_key": key}, None


def _signup_claims(data):
    return read_step_token(data.get("google_signup_token"), GOOGLE_SIGNUP)


@bp.before_request
def google_switched_on():
    if current_app.google_verifier is None:
        return error("google_disabled", 404)


@bp.post("/auth/google")
def google_sign_in():
    """{id_token}. A known Google account signs in. A new one gets a short-lived google_signup_token
    for /auth/google/register or /auth/google/link; no account is made yet."""
    google, failed = _from_google(json_body().get("id_token"))
    if failed:
        return failed
    known = query("""UPDATE user_identities SET last_login_at = now(), email = %s
                     WHERE provider = 'google' AND subject = %s RETURNING user_id""",
                  (google["email"], google["sub"]), one=True)
    if known:
        user = query("SELECT * FROM users WHERE id = %s", (known["user_id"],), one=True)
        return jsonify({"status": "signed_in", "token": make_token(user), "user": public_user(user)})
    has_account = query("SELECT 1 FROM users WHERE email_key = %s", (google["email_key"],), one=True) is not None
    token = make_step_token(GOOGLE_SIGNUP, google_sub=google["sub"], email=google["email"],
                            email_key=google["email_key"], name=google["name"])
    return jsonify({"status": "registration_required", "google_signup_token": token,
                    "expires_in": current_app.config["STEP_TOKEN_MINUTES"] * 60,
                    "profile": {"name": google["name"], "email": google["email"]},
                    # fine to say: Google has just proved this person owns the mailbox
                    "email_has_account": has_account})


@bp.post("/auth/google/register")
def google_register():
    """{google_signup_token, phone, name?, neighbourhood_id?, household?, business?}: a new account with
    Google's verified email and no password. A phone or email that already has an account answers 409
    with can_link: the person can link Google to it instead (with that account's password)."""
    data = json_body()
    google = _signup_claims(data)
    if google is None:
        return error("google_signup_expired", 401)
    # registered already (the same sign-up token used twice): say so, rather than "email taken"
    if query("SELECT 1 FROM user_identities WHERE provider = 'google' AND subject = %s",
             (google["google_sub"],), one=True):
        return error("google_already_linked", 409)
    name = str(data.get("name") or google["name"] or "").strip()
    phone = str(data.get("phone") or "").strip()
    if not (name and phone):
        return error("missing_fields", 400)
    phone, problem = phones.normalise(phone)
    if problem:
        return error(problem, 400)
    profile, problems = accounts.validate_signup({**data, "name": name})
    if problems:
        return error("invalid_profile", 400, fields=problems)
    user, taken = accounts.create_account(name, phone, None, profile["neighbourhood_id"], google["email"],
                                          google["email_key"], profile["places"], google_sub=google["google_sub"])
    if taken == "google_already_linked":
        return error(taken, 409)
    if taken:
        return error(taken, 409, can_link=True)
    return jsonify({"token": make_token(user), "user": public_user(user)}), 201


@bp.post("/auth/google/link")
def google_link():
    """{google_signup_token, login, password}: add Google to an existing account. Its password is
    required: Google proves who the person is, the password proves the account is theirs."""
    data = json_body()
    google = _signup_claims(data)
    if google is None:
        return error("google_signup_expired", 401)
    user = password_user(data.get("login"), data.get("password"))
    if user is None:
        return error("bad_login", 401)
    if user["role"] == "staff":                  # the dashboard stays behind its own password
        return error("forbidden", 403)
    try:
        with savepoint():
            query("""INSERT INTO user_identities (user_id, provider, subject, email, last_login_at)
                     VALUES (%s, 'google', %s, %s, now())""", (user["id"], google["google_sub"], google["email"]))
    except psycopg.errors.UniqueViolation:       # this Google account, or this person, is linked already
        return error("google_already_linked", 409)
    if user["email"] is None:
        # an account from before emails: Google's verified one becomes its email, unless another
        # account has that mailbox (then it stays without one; signing in with Google still works)
        try:
            with savepoint():
                user = query("""UPDATE users SET email = %s, email_key = %s, email_verified_at = now()
                                WHERE id = %s RETURNING *""",
                             (google["email"], google["email_key"], user["id"]), one=True)
        except psycopg.errors.UniqueViolation:
            pass
    return jsonify({"token": make_token(user), "user": public_user(user)})
