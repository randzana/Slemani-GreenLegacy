"""Phone numbers in one form (E.164, +9647501234567) wherever they are stored or looked up.

Without it 07501234567 and +9647501234567 would be two "different" numbers: two accounts for one
phone, and a login that fails when the person types it the other way. The phone is not verified
(the email is the verified identity), but it stays unique and old accounts log in with it.
Migration 007 converts the rows written before this, with the same rules for Iraqi mobiles.
"""
import phonenumbers
from flask import current_app, has_app_context

from .config import Config


def _setting(name):
    return current_app.config[name] if has_app_context() else getattr(Config, name)


def normalise(raw):
    """(E.164, None) for a valid number from an allowed country, else (None, error code)."""
    try:
        number = phonenumbers.parse(str(raw or "").strip(), _setting("PHONE_REGION"))
    except phonenumbers.NumberParseException:
        return None, "invalid_phone"
    if not phonenumbers.is_valid_number(number):
        return None, "invalid_phone"
    if str(number.country_code) not in _setting("PHONE_ALLOWED_COUNTRY_CODES"):
        return None, "phone_not_allowed"
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164), None


def login_candidates(raw):
    """What a typed login phone can be stored as: the normalised form first, then the text exactly
    as typed, for the few old rows 007 left alone because they were not an Iraqi mobile number."""
    typed = str(raw or "").strip()
    e164, _ = normalise(typed)
    return [p for p in dict.fromkeys((e164, typed)) if p]
