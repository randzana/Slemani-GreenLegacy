"""Email codes (app/otp.py): one person, one mailbox, a few guesses, and nothing worth stealing in the
database or the logs."""
import logging
import smtplib

import psycopg
import pytest

from app import auth, emails, otp
from conftest import TEST_DB
from test_races import at_once

EMAIL = "rand@example.com"


def ask(client, email=EMAIL):
    return client.post("/auth/otp/request", json={"email": email})


def answer(client, code, email=EMAIL):
    return client.post("/auth/otp/verify", json={"email": email, "code": code})


def sql(statement, params=()):
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else None


def sent_code(app, email=EMAIL):
    return app.otp_sender.last_code(email)


def wrong(code):
    return f"{(int(code) + 1) % 10 ** len(code):0{len(code)}d}"


def later():
    """As if the resend wait has passed: move every code back two minutes."""
    sql("UPDATE otp_codes SET created_at = created_at - interval '2 minutes'")


# ---------------------------------------------------------------- the normal way

def test_request_then_verify_gives_a_step_token(client, app):
    r = ask(client)
    assert r.status_code == 200 and r.json == {"sent": True, "expires_in": 300, "resend_in": 60}
    code = sent_code(app)
    assert len(code) == 6 and code.isdigit()

    ok = answer(client, code)
    assert ok.status_code == 200 and ok.json["email_has_account"] is False and ok.json["expires_in"] == 600
    with app.app_context():
        claims = auth.read_step_token(ok.json["email_verification_token"], otp.EMAIL_VERIFIED)
    assert claims["email"] == EMAIL and claims["email_key"] == EMAIL


def test_one_mailbox_however_it_is_spelled(client, app):
    assert ask(client, "John.Doe+green@Gmail.com").status_code == 200
    assert ask(client, "johndoe@googlemail.com").json["error"] == "otp_too_soon"    # same mailbox, same wait
    code = sent_code(app, "john.doe+green@gmail.com")                  # mail goes to the address as written
    ok = answer(client, code, "JohnDoe@gmail.com")
    assert ok.status_code == 200
    with app.app_context():
        claims = auth.read_step_token(ok.json["email_verification_token"], otp.EMAIL_VERIFIED)
    assert claims["email_key"] == "johndoe@gmail.com" and claims["email"] == "johndoe@gmail.com"


def test_the_answer_does_not_say_whether_the_mailbox_has_an_account(client, app):
    sql("""UPDATE users SET email = 'staff@example.com', email_key = 'staff@example.com',
                            email_verified_at = now() WHERE role = 'staff'""")
    known, unknown = ask(client, "staff@example.com"), ask(client, "nobody@example.com")
    assert (known.status_code, known.json) == (unknown.status_code, unknown.json)
    # after the code is answered it may say so: the caller has just proved they read that mailbox
    assert answer(client, sent_code(app, "staff@example.com"), "staff@example.com").json["email_has_account"] is True
    assert answer(client, sent_code(app, "nobody@example.com"), "nobody@example.com").json["email_has_account"] is False


def test_bad_input(client):
    for bad in ("", None, "not-an-email", "a@b", "two@@example.com", "+tag@gmail.com", "x" * 250 + "@example.com"):
        r = ask(client, bad)
        assert r.status_code == 400 and r.json["error"] == "invalid_email", bad
        assert r.json["message"] != "invalid_email"          # the Kurdish text, not the code
    assert ask(client).status_code == 200
    assert client.post("/auth/otp/verify", json={"email": EMAIL}).json["error"] == "missing_fields"
    assert client.post("/auth/otp/verify", json={"email": "nope", "code": "123456"}).json["error"] == "invalid_email"
    for body in ([EMAIL], "rand@example.com", 42):           # JSON, but not an object: 400, not a crash
        assert client.post("/auth/otp/request", json=body).json["error"] == "invalid_email"
        assert client.post("/auth/otp/verify", json=body).json["error"] == "invalid_email"


# ---------------------------------------------------------------- nothing worth stealing

def test_no_code_in_the_database_the_answer_or_the_logs(client, app, caplog):
    caplog.set_level(logging.DEBUG)
    r = ask(client)
    code = sent_code(app)
    assert code not in r.get_data(as_text=True)
    rows = sql("SELECT * FROM otp_codes")
    assert len(rows) == 1 and not any(code in str(value) for value in rows[0])
    with app.app_context():                                  # what is stored is the keyed hash
        assert sql("SELECT code_hash FROM otp_codes") == [(otp.code_hash(EMAIL, "verify_email", code),)]
    ok = answer(client, code)
    assert code not in ok.get_data(as_text=True)
    assert code not in caplog.text and EMAIL not in caplog.text and emails.masked(EMAIL) in caplog.text


def test_the_console_sender_is_the_one_place_a_code_is_written(caplog):
    caplog.set_level(logging.WARNING)
    otp.ConsoleOtpSender().send("rand@example.com", "123456")
    assert "123456" in caplog.text and "ra***@example.com" in caplog.text and "rand@example.com" not in caplog.text


# ---------------------------------------------------------------- guesses

def test_five_wrong_guesses_then_the_code_is_dead_and_the_count_survives(client, app):
    ask(client)
    code = sent_code(app)
    for left in (4, 3, 2, 1, 0):
        r = answer(client, wrong(code))
        assert (r.status_code, r.json["error"], r.json["attempts_left"]) == (400, "otp_invalid", left)
    # each count was committed even though each answer was an error
    assert sql("SELECT attempts FROM otp_codes") == [(5,)]
    locked = answer(client, code)                            # the right code, too late
    assert locked.status_code == 429 and locked.json["error"] == "otp_locked"
    later()
    ask(client)                                              # a new code starts again
    assert answer(client, sent_code(app)).status_code == 200


def test_parallel_guesses_take_turns(app):
    """Twenty wrong guesses at the same moment still get five tries between them."""
    app.test_client().post("/auth/otp/request", json={"email": EMAIL})
    bad = wrong(sent_code(app))
    results = at_once(20, lambda i: answer(app.test_client(), bad).json["error"])
    assert results.count("otp_invalid") == 5 and results.count("otp_locked") == 15
    assert sql("SELECT attempts FROM otp_codes") == [(5,)]


def test_an_expired_code_fails(client, app):
    ask(client)
    sql("UPDATE otp_codes SET expires_at = now() - interval '1 second'")
    r = answer(client, sent_code(app))
    assert r.status_code == 400 and r.json["error"] == "otp_expired"


def test_a_code_works_once(client, app):
    ask(client)
    code = sent_code(app)
    assert answer(client, code).status_code == 200
    again = answer(client, code)
    assert again.status_code == 400 and again.json["error"] == "otp_expired"


def test_a_new_code_replaces_the_old_one(client, app):
    ask(client)
    first = sent_code(app)
    later()
    ask(client)
    second = sent_code(app)
    if first != second:                    # the same six digits twice is possible, if unlikely
        r = answer(client, first)
        assert r.status_code == 400 and r.json["error"] == "otp_invalid"
    assert answer(client, second).status_code == 200
    assert sql("SELECT count(*) FROM otp_codes WHERE superseded_at IS NOT NULL") == [(1,)]


def test_two_right_answers_at_once_make_one_success(app):
    app.test_client().post("/auth/otp/request", json={"email": EMAIL})
    code = sent_code(app)
    statuses = at_once(5, lambda i: answer(app.test_client(), code).status_code)
    assert sorted(statuses) == [200, 400, 400, 400, 400]


# ---------------------------------------------------------------- how often

def test_a_second_code_waits_a_minute(client, app):
    ask(client)
    r = ask(client)
    assert r.status_code == 429 and r.json["error"] == "otp_too_soon" and 0 < r.json["retry_after"] <= 60
    later()
    assert ask(client).status_code == 200


def test_hourly_caps_per_mailbox_per_ip_and_overall(client, app):
    app.config["OTP_RESEND_SECONDS"] = 0
    for _ in range(5):
        assert ask(client).status_code == 200
    r = ask(client)
    assert r.status_code == 429 and r.json["error"] == "otp_rate_limited" and 3500 < r.json["retry_after"] <= 3600

    app.config["OTP_MAX_PER_IP_HOUR"] = 7                   # 5 to rand@ already came from this address
    assert ask(client, "a@example.com").status_code == 200
    assert ask(client, "b@example.com").status_code == 200
    assert ask(client, "c@example.com").json["error"] == "otp_rate_limited"
    other_ip = client.post("/auth/otp/request", json={"email": "c@example.com"},
                           environ_base={"REMOTE_ADDR": "10.0.0.9"})
    assert other_ip.status_code == 200

    app.config["OTP_MAX_PER_HOUR"] = 8                      # everyone together
    late = client.post("/auth/otp/request", json={"email": "d@example.com"}, environ_base={"REMOTE_ADDR": "10.0.0.10"})
    assert late.status_code == 429 and late.json["error"] == "otp_rate_limited"


def test_parallel_requests_leave_one_live_code(app):
    statuses = at_once(5, lambda i: app.test_client().post("/auth/otp/request", json={"email": EMAIL}).status_code)
    assert sorted(statuses) == [200, 429, 429, 429, 429]
    assert sql("""SELECT count(*) FROM otp_codes WHERE consumed_at IS NULL AND superseded_at IS NULL""") == [(1,)]
    assert len(app.otp_sender.sent) == 1


def test_codes_are_forgotten_after_a_day(client, app):
    ask(client, "old@example.com")
    sql("UPDATE otp_codes SET created_at = now() - interval '25 hours'")
    ask(client)
    assert sql("SELECT email_key FROM otp_codes") == [(EMAIL,)]


# ---------------------------------------------------------------- delivery

def test_when_the_mail_cannot_be_sent_nothing_is_kept(client, app):
    ask(client)
    first = sent_code(app)
    later()
    app.otp_sender.fail = True
    r = ask(client)
    assert r.status_code == 503 and r.json["error"] == "otp_send_failed"
    assert sql("SELECT count(*) FROM otp_codes") == [(1,)]          # the failed code was undone ...
    assert answer(client, first).status_code == 200                 # ... and the old one still works
    app.otp_sender.fail = False
    later()
    assert ask(client).status_code == 200                           # no wait: nothing was sent


class FakeSMTP:
    """Stands in for smtplib.SMTP / SMTP_SSL: records what the sender does, sends nothing."""
    made = []

    def __init__(self, host, port, timeout=None, context=None):
        self.where, self.calls, self.message = (host, port), [], None
        FakeSMTP.made.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user))

    def send_message(self, message):
        self.message = message


def test_smtp_sender_writes_a_kurdish_email(monkeypatch):
    FakeSMTP.made.clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    sender = otp.SmtpOtpSender("smtp.example.com", 587, "bot@example.com", "pw", "bot@example.com", "starttls", 5)
    sender.send("rand@example.com", "654321")
    smtp = FakeSMTP.made[0]
    assert smtp.where == ("smtp.example.com", 587) and smtp.calls == ["starttls", ("login", "bot@example.com")]
    assert smtp.message["To"] == "rand@example.com" and smtp.message["Subject"] == otp.EMAIL_CODE_SUBJECT
    body = smtp.message.get_content()
    assert "654321" in body and "5 خولەک" in body

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    otp.SmtpOtpSender("smtp.example.com", 465, "", "", "bot@example.com", "ssl", 5).send("rand@example.com", "1")
    assert FakeSMTP.made[1].calls == []                      # implicit TLS, no login without a user


def test_smtp_failure_becomes_otp_send_error(monkeypatch):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError("no mail server")
    monkeypatch.setattr(smtplib, "SMTP", refuse)
    sender = otp.SmtpOtpSender("smtp.example.com", 587, "", "", "bot@example.com", "starttls", 5)
    with pytest.raises(otp.OtpSendError):
        sender.send("rand@example.com", "123456")


def test_choosing_the_sender():
    base = {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": 587, "SMTP_USER": "bot@example.com",
            "SMTP_PASSWORD": "pw", "SMTP_FROM": "", "SMTP_SECURITY": "starttls", "OTP_TTL_SECONDS": 300}
    assert isinstance(otp.make_otp_sender({**base, "OTP_SENDER": "console"}), otp.ConsoleOtpSender)
    assert isinstance(otp.make_otp_sender({**base, "OTP_SENDER": "fake"}), otp.FakeOtpSender)
    smtp = otp.make_otp_sender({**base, "OTP_SENDER": "smtp"})
    assert smtp.sender == "bot@example.com" and smtp.minutes == 5
    for broken in ({"OTP_SENDER": "sms"}, {"OTP_SENDER": "smtp", "SMTP_HOST": ""},
                   {"OTP_SENDER": "smtp", "SMTP_SECURITY": "tls"}):
        with pytest.raises(ValueError):
            otp.make_otp_sender({**base, **broken})
