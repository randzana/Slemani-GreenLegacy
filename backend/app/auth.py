"""Sign up, log in and the JWT decorators."""
import datetime as dt
from functools import wraps

import jwt
import psycopg
from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from . import phones
from .db import query
from .strings import reason

bp = Blueprint("auth", __name__)


def error(code, status):
    return jsonify({"error": code, "message": reason(code)}), status


# Every token says what it is for (typ). Only an access token is a login; a step token proves one step
# of signing up (the email was verified, or who Google says this new person is), lives a few minutes,
# carries this audience, and is accepted only by the endpoint for that step. One SECRET_KEY signs them
# all, so without typ a step token would pass wherever any valid signature does.
ACCESS = "access"
STEP_AUDIENCE = "gl-step"
MAX_USER_ID = 2**31 - 1        # users.id is an INTEGER; a bigger number is not one of ours


def make_token(user):
    payload = {
        "typ": ACCESS,
        "sub": str(user["id"]),
        "role": user["role"],
        "iat": dt.datetime.now(dt.timezone.utc),
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=current_app.config["JWT_DAYS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def make_step_token(typ, **claims):
    now = dt.datetime.now(dt.timezone.utc)
    payload = {**claims, "typ": typ, "aud": STEP_AUDIENCE, "iat": now,
               "exp": now + dt.timedelta(minutes=current_app.config["STEP_TOKEN_MINUTES"])}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def read_step_token(token, typ):
    """The claims of an unexpired step token of exactly this typ, else None."""
    try:
        payload = jwt.decode(str(token or ""), current_app.config["SECRET_KEY"], algorithms=["HS256"],
                             audience=STEP_AUDIENCE, options={"require": ["typ", "aud", "exp"]})
    except jwt.PyJWTError:
        return None
    return payload if payload["typ"] == typ else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return error("unauthorized", 401)
        try:
            # a token with an audience (every step token) is refused here, as no audience is expected
            payload = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
            user_id = int(payload["sub"])
        except (jwt.PyJWTError, KeyError, TypeError, ValueError):
            return error("unauthorized", 401)
        # tokens from before typ existed are logins; any other typ is not
        if payload.get("typ", ACCESS) != ACCESS or not 0 < user_id <= MAX_USER_ID:
            return error("unauthorized", 401)
        user = query("SELECT * FROM users WHERE id = %s", (user_id,), one=True)
        # After a re-seed the same id belongs to someone else: a token issued before this account
        # existed must not log in as them (2 s of slack for the clock and the rounding of iat).
        if user is None or payload.get("iat", 0) + 2 < user["created_at"].timestamp():
            return error("unauthorized", 401)
        g.user = user
        return fn(*args, **kwargs)
    return wrapper


def staff_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if g.user["role"] != "staff":
            return error("forbidden", 403)
        return fn(*args, **kwargs)
    return wrapper


def public_user(user):
    return {k: user[k] for k in ("id", "name", "phone", "neighbourhood_id", "role")}


@bp.post("/auth/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name, phone, password = (data.get(k, "").strip() for k in ("name", "phone", "password"))
    if not (name and phone and len(password) >= 6):
        return error("missing_fields", 400)
    phone, problem = phones.normalise(phone)
    if problem:
        return error(problem, 400)
    try:
        user = query(
            """INSERT INTO users (name, phone, password_hash, neighbourhood_id)
               VALUES (%s, %s, %s, %s) RETURNING *""",
            (name, phone, generate_password_hash(password), data.get("neighbourhood_id")),
            one=True,
        )
    except psycopg.errors.UniqueViolation:
        return error("phone_taken", 409)
    return jsonify({"token": make_token(user), "user": public_user(user)}), 201


@bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    user = None
    for phone in phones.login_candidates(data.get("phone")):
        user = query("SELECT * FROM users WHERE phone = %s", (phone,), one=True)
        if user:
            break
    # a Google-only account has no password, so no password opens it
    if user is None or not user["password_hash"] or not check_password_hash(user["password_hash"],
                                                                               str(data.get("password", ""))):
        return error("bad_login", 401)
    return jsonify({"token": make_token(user), "user": public_user(user)})


@bp.get("/neighbourhoods")
def neighbourhoods():
    """The list for signup. ?geo=1 adds each boundary as GeoJSON, null until tools/import_boundaries.py
    has loaded one (6 decimals is about 10 cm, plenty for a map and a much smaller reply)."""
    if request.args.get("geo") in ("1", "true"):
        return jsonify(query("""SELECT id, name, ST_AsGeoJSON(boundary, 6)::json AS boundary
                                FROM neighbourhoods ORDER BY name"""))
    return jsonify(query("SELECT id, name FROM neighbourhoods ORDER BY name"))
