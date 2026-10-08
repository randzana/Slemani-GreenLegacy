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
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=current_app.config["JWT_DAYS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "unauthorized"}), 401
        try:
            payload = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.PyJWTError:
            return jsonify({"error": "unauthorized"}), 401
        user = query("SELECT * FROM users WHERE id = %s", (int(payload["sub"]),), one=True)
        if user is None:
            return jsonify({"error": "unauthorized"}), 401
        g.user = user
        return fn(*args, **kwargs)
    return wrapper


def staff_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if g.user["role"] != "staff":
            return jsonify({"error": "forbidden"}), 403
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
    return jsonify(query("SELECT id, name FROM neighbourhoods ORDER BY name"))
