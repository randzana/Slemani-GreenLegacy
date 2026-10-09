"""Email addresses: a light check of the form, and one key per mailbox.

The verified email is the identity of an account, one account per mailbox. Some providers deliver
several spellings to one mailbox (Gmail ignores dots, and anything after a + goes to the same inbox),
so users.email_key is what those spellings share; otherwise every Gmail address would be many
accounts. Mail is always sent to the address as the person wrote it, never to the key.
"""
import re

MAX_LENGTH = 254
# something@something.tld; the emailed code proves the rest, so no stricter rules here
_FORM = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s.]+$")
GMAIL = {"gmail.com", "googlemail.com"}
PLUS_TAGS = GMAIL | {"outlook.com", "hotmail.com", "live.com", "icloud.com", "me.com"}


def normalise(raw):
    """(email in lower case, its mailbox key, None), or (None, None, 'invalid_email')."""
    email = str(raw or "").strip().lower()
    if len(email) > MAX_LENGTH or not _FORM.match(email):
        return None, None, "invalid_email"
    local, _, domain = email.rpartition("@")
    if domain in PLUS_TAGS:
        local = local.split("+", 1)[0]
    if domain in GMAIL:
        local, domain = local.replace(".", ""), "gmail.com"
    if not local:
        return None, None, "invalid_email"
    return email, f"{local}@{domain}", None


def masked(email):
    """ra***@gmail.com, for logs: enough to tell two people apart, not enough to write to them."""
    local, _, domain = str(email or "").rpartition("@")
    return f"{local[:2]}***@{domain}" if local else "***"
