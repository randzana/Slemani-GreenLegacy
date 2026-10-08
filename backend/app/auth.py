"""Sign up, log in and the JWT decorators."""
import datetime as dt
from functools import wraps

import jwt
import psycopg
from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import query
from .strings import reason

bp = Blueprint("auth", __name__)


def error(code, status):
    return jsonify({"error": code, "message": reason(code)}), status


def make_token(user):
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "iat": dt.datetime.now(dt.timezone.utc),
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=current_app.config["JWT_DAYS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return error("unauthorized", 401)
        try:
            payload = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.PyJWTError:
            return error("unauthorized", 401)
        user = query("SELECT * FROM users WHERE id = %s", (int(payload["sub"]),), one=True)
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
    user = query("SELECT * FROM users WHERE phone = %s", (data.get("phone", "").strip(),), one=True)
    if user is None or not check_password_hash(user["password_hash"], data.get("password", "")):
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
