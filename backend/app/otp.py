"""Email codes: six digits that prove a person reads a mailbox, the first step of signing up.

We make and check the codes; a sender only delivers them, and is injected through create_app like
the detector: console (writes the code to the server log: the demo laptop has no mail account and
maybe no internet), fake (tests) or smtp (real mail).

The rules, and why:
- Only HMAC(OTP_PEPPER, mailbox|purpose|code) is stored, so a copy of the database holds no codes.
- A code lives OTP_TTL_SECONDS and allows OTP_MAX_ATTEMPTS guesses. A wrong guess is counted with an
  UPDATE and the 400 is *returned*: close_db rolls back when a request raises, so a raised error would
  undo the count and leave the code open to unlimited guessing.
- The live code is read FOR UPDATE, so guesses for one mailbox take turns: twenty parallel guesses
  still get five tries, and two right answers at once make one account.
- A new code waits OTP_RESEND_SECONDS; there are hourly caps per mailbox, per IP address and for
  everyone together (which protects the mail account). Requests for one mailbox take turns (an
  advisory lock until the request ends), so two at once send one mail; the other caps are counted
  before the insert, so a burst from many mailboxes can pass them by a few.
- /auth/otp/request answers the same whether or not the mailbox has an account.
- Codes are forgotten after a day: the address and IP address are personal data.
"""
import hashlib
import hmac
import logging
import math
import secrets
import smtplib
import ssl
from email.message import EmailMessage

import psycopg
from flask import Blueprint, current_app, jsonify, request

from . import emails
from .auth import error, json_body, make_step_token
from .db import get_db, query
from .strings import EMAIL_CODE_BODY, EMAIL_CODE_SUBJECT

log = logging.getLogger(__name__)
bp = Blueprint("otp", __name__)

VERIFY_EMAIL = "verify_email"
EMAIL_VERIFIED = "email_verified"          # the step token's typ (app/auth.py)


class OtpSendError(Exception):
    """The code could not be handed to the mail system."""


class ConsoleOtpSender:
    """The code goes to the server's terminal. Anyone who can read that terminal can verify any
    address, so this is for the demo laptop only (preflight warns)."""
    name = "console"

    def send(self, email, code):
        log.warning("EMAIL CODE for %s: %s   (OTP_SENDER=console: demo only)", emails.masked(email), code)


class FakeOtpSender:
    """For tests: keeps what was sent, and can be told to fail."""
    name = "fake"

    def __init__(self):
        self.sent = []
        self.fail = False

    def send(self, email, code):
        if self.fail:
            raise OtpSendError("fake sender told to fail")
        self.sent.append((email, code))

    def last_code(self, email):
        return next((code for to, code in reversed(self.sent) if to == email), None)


class SmtpOtpSender:
    """Real mail through any SMTP account (SMTP_* settings). security: starttls (port 587),
    ssl (port 465) or none (a relay on the same machine)."""
    name = "smtp"

    def __init__(self, host, port, user, password, sender, security, minutes, timeout=15):
        if not host or not sender:
            raise ValueError("OTP_SENDER=smtp needs SMTP_HOST and SMTP_FROM (or SMTP_USER)")
        if security not in ("starttls", "ssl", "none"):
            raise ValueError(f"SMTP_SECURITY={security!r}: use starttls, ssl or none")
        self.host, self.port, self.user, self.password = host, port, user, password
        self.sender, self.security, self.minutes, self.timeout = sender, security, minutes, timeout

    def send(self, email, code):
        message = EmailMessage()
        message["Subject"], message["From"], message["To"] = EMAIL_CODE_SUBJECT, self.sender, email
        message.set_content(EMAIL_CODE_BODY.format(code=code, minutes=self.minutes))
        try:
            if self.security == "ssl":
                smtp = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout,
                                        context=ssl.create_default_context())
            else:
                smtp = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            with smtp:
                if self.security == "starttls":
                    smtp.starttls(context=ssl.create_default_context())
                if self.user:
                    smtp.login(self.user, self.password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise OtpSendError(type(exc).__name__) from exc


def make_otp_sender(cfg):
    kind = cfg.get("OTP_SENDER", "console")
    if kind == "console":
        return ConsoleOtpSender()
    if kind == "fake":
        return FakeOtpSender()
    if kind == "smtp":
        return SmtpOtpSender(cfg["SMTP_HOST"], cfg["SMTP_PORT"], cfg["SMTP_USER"], cfg["SMTP_PASSWORD"],
                             cfg["SMTP_FROM"] or cfg["SMTP_USER"], cfg["SMTP_SECURITY"],
                             max(1, cfg["OTP_TTL_SECONDS"] // 60))
    raise ValueError(f"OTP_SENDER={kind!r}: use console, fake or smtp")


def code_hash(email_key, purpose, code):
    cfg = current_app.config
    # without OTP_PEPPER, a key derived from SECRET_KEY under a fixed label (preflight warns)
    pepper = cfg["OTP_PEPPER"].encode() if cfg["OTP_PEPPER"] else hmac.new(
        cfg["SECRET_KEY"].encode(), b"greenlegacy email code pepper", hashlib.sha256).digest()
    return hmac.new(pepper, f"{email_key}|{purpose}|{code}".encode(), hashlib.sha256).hexdigest()


def _hourly(where, params):
    """How many codes went out in the last hour in this scope, and when the oldest leaves the window."""
    return query(f"""SELECT count(*) AS n, EXTRACT(EPOCH FROM min(created_at) + interval '1 hour' - now())
                            AS frees_in
                     FROM otp_codes WHERE {where} AND created_at > now() - interval '1 hour'""",
                 params, one=True)


def _seconds(value):
    return max(1, math.ceil(float(value or 0)))


def send_code(email, email_key, ip, purpose=VERIFY_EMAIL):
    cfg = current_app.config
    # without this, a request that checked the wait just before a parallel one committed would
    # supersede that fresh code and send a second mail
    query("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"otp:{purpose}:{email_key}",))
    query("DELETE FROM otp_codes WHERE created_at < now() - interval '1 day'")

    last = query("""SELECT EXTRACT(EPOCH FROM now() - max(created_at)) AS ago FROM otp_codes
                    WHERE email_key = %s AND purpose = %s""", (email_key, purpose), one=True)
    if last["ago"] is not None and last["ago"] < cfg["OTP_RESEND_SECONDS"]:
        return error("otp_too_soon", 429, retry_after=_seconds(cfg["OTP_RESEND_SECONDS"] - last["ago"]))
    for where, params, cap in (("email_key = %s", (email_key,), cfg["OTP_MAX_PER_EMAIL_HOUR"]),
                               ("request_ip = %s::inet", (ip,), cfg["OTP_MAX_PER_IP_HOUR"]),
                               ("true", (), cfg["OTP_MAX_PER_HOUR"])):
        sent = _hourly(where, params)
        if sent["n"] >= cap:
            return error("otp_rate_limited", 429, retry_after=_seconds(sent["frees_in"]))

    code = f"{secrets.randbelow(10 ** cfg['OTP_LENGTH']):0{cfg['OTP_LENGTH']}d}"
    try:
        # a savepoint: if the mail cannot be sent the new code is undone and the old one stays live
        with get_db().transaction():
            query("""UPDATE otp_codes SET superseded_at = now()
                     WHERE email_key = %s AND purpose = %s AND consumed_at IS NULL AND superseded_at IS NULL""",
                  (email_key, purpose))
            query("""INSERT INTO otp_codes (email_key, purpose, code_hash, expires_at, request_ip)
                     VALUES (%s, %s, %s, now() + make_interval(secs => %s), %s::inet)""",
                  (email_key, purpose, code_hash(email_key, purpose, code), cfg["OTP_TTL_SECONDS"], ip))
            current_app.otp_sender.send(email, code)
    except psycopg.errors.UniqueViolation:       # a second lock on the same door: should not happen
        return error("otp_too_soon", 429, retry_after=_seconds(cfg["OTP_RESEND_SECONDS"]))
    except OtpSendError as exc:
        log.warning("email code to %s not sent: %s", emails.masked(email), exc)
        return error("otp_send_failed", 503)
    log.info("email code sent to %s", emails.masked(email))
    return jsonify({"sent": True, "expires_in": cfg["OTP_TTL_SECONDS"], "resend_in": cfg["OTP_RESEND_SECONDS"]})


def check_code(email, email_key, code, purpose=VERIFY_EMAIL):
    cfg = current_app.config
    live = query("""SELECT id, code_hash, attempts, expires_at <= now() AS expired FROM otp_codes
                    WHERE email_key = %s AND purpose = %s AND consumed_at IS NULL AND superseded_at IS NULL
                    FOR UPDATE""", (email_key, purpose), one=True)
    if live is None:                               # never sent, already used, or forgotten
        return error("otp_expired", 400)
    if live["attempts"] >= cfg["OTP_MAX_ATTEMPTS"]:
        return error("otp_locked", 429)
    if live["expired"]:
        return error("otp_expired", 400)
    if not hmac.compare_digest(live["code_hash"], code_hash(email_key, purpose, code)):
        tried = query("UPDATE otp_codes SET attempts = attempts + 1 WHERE id = %s RETURNING attempts",
                      (live["id"],), one=True)["attempts"]
        return error("otp_invalid", 400, attempts_left=max(cfg["OTP_MAX_ATTEMPTS"] - tried, 0))
    used = query("""UPDATE otp_codes SET consumed_at = now()
                    WHERE id = %s AND consumed_at IS NULL AND superseded_at IS NULL
                      AND expires_at > now() AND attempts < %s RETURNING id""",
                 (live["id"], cfg["OTP_MAX_ATTEMPTS"]), one=True)
    if used is None:
        return error("otp_expired", 400)
    known = query("SELECT 1 FROM users WHERE email_key = %s", (email_key,), one=True) is not None
    return jsonify({"email_verification_token": make_step_token(EMAIL_VERIFIED, email=email, email_key=email_key),
                    "expires_in": cfg["STEP_TOKEN_MINUTES"] * 60,
                    # fine to say here: the caller has just proved they read this mailbox
                    "email_has_account": known})


@bp.post("/auth/otp/request")
def otp_request():
    email, key, problem = emails.normalise(json_body().get("email"))
    if problem:
        return error(problem, 400)
    return send_code(email, key, request.remote_addr)


@bp.post("/auth/otp/verify")
def otp_verify():
    data = json_body()
    email, key, problem = emails.normalise(data.get("email"))
    if problem:
        return error(problem, 400)
    code = str(data.get("code") or "").strip()
    if not code:
        return error("missing_fields", 400)
    return check_code(email, key, code)
