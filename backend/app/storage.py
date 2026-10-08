"""Saves uploaded photos and frames as files (not in the database) with random names."""
import secrets
from pathlib import Path

from flask import current_app

ALLOWED = {".jpg", ".jpeg", ".png", ".webp"}


def save_upload(file_storage, prefix):
    ext = Path(file_storage.filename or "").suffix.lower()
    if ext not in ALLOWED:
        ext = ".jpg"
    name = f"{prefix}_{secrets.token_hex(8)}{ext}"
    folder = Path(current_app.config["UPLOAD_DIR"])
    folder.mkdir(parents=True, exist_ok=True)
    file_storage.save(folder / name)
    return name


def path_of(name):
    return Path(current_app.config["UPLOAD_DIR"]) / name


def url_of(name):
    return f"/files/{name}"
