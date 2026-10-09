"""Settings. Everything comes from environment variables so nothing secret lives in the code."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

_env_file = BASE_DIR / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))


def _int(name, default):
    return int(os.environ.get(name, default))


def _float(name, default):
    return float(os.environ.get(name, default))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "practice-only-secret-change-me-before-any-pilot")
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://gl:gl@localhost:5432/greenlegacy")
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", str(BASE_DIR / "uploads"))
    JWT_DAYS = _int("JWT_DAYS", 7)
    # Lifetime of a sign-up step token (email verified, or a new Google sign-in): app/auth.py
    STEP_TOKEN_MINUTES = _int("STEP_TOKEN_MINUTES", 10)

    # Email codes for signing up (app/otp.py). OTP_SENDER: console writes the code to the server log
    # (the demo laptop: no mail account needed, works offline; never for a pilot), fake (tests), or
    # smtp (real mail through SMTP_*). OTP_PEPPER keys the stored code hashes; without it a key is
    # derived from SECRET_KEY (preflight warns).
    OTP_SENDER = os.environ.get("OTP_SENDER", "console")
    OTP_PEPPER = os.environ.get("OTP_PEPPER", "")
    OTP_LENGTH = _int("OTP_LENGTH", 6)
    OTP_TTL_SECONDS = _int("OTP_TTL_SECONDS", 300)
    OTP_MAX_ATTEMPTS = _int("OTP_MAX_ATTEMPTS", 5)
    OTP_RESEND_SECONDS = _int("OTP_RESEND_SECONDS", 60)
    OTP_MAX_PER_EMAIL_HOUR = _int("OTP_MAX_PER_EMAIL_HOUR", 5)
    OTP_MAX_PER_IP_HOUR = _int("OTP_MAX_PER_IP_HOUR", 20)
    OTP_MAX_PER_HOUR = _int("OTP_MAX_PER_HOUR", 200)        # all mail together: protects the mail account
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = _int("SMTP_PORT", 587)
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "")             # empty: SMTP_USER
    SMTP_SECURITY = os.environ.get("SMTP_SECURITY", "starttls")   # starttls (587), ssl (465) or none

    # Accounts. Phones are stored in E.164 (app/phones.py); a number without a country code is
    # read as PHONE_REGION's, and only these country calling codes are accepted.
    PHONE_REGION = os.environ.get("PHONE_REGION", "IQ")
    PHONE_ALLOWED_COUNTRY_CODES = tuple(
        c.strip().lstrip("+") for c in os.environ.get("PHONE_ALLOWED_COUNTRY_CODES", "964").split(",") if c.strip())
    # A new account needs a verified email. 0 lets old app builds sign up without one: an offline
    # rehearsal only (preflight warns).
    OTP_REQUIRED = os.environ.get("OTP_REQUIRED", "1") != "0"
    # Sign in with Google (app/google_auth.py); off while GOOGLE_CLIENT_IDS is empty. The IDs are the
    # OAuth clients whose tokens are accepted (Web, Android, iOS; comma-separated). GOOGLE_SERVER_CLIENT_ID
    # is the Web one: the app gets it from /auth/config and asks Google for tokens issued to it.
    GOOGLE_CLIENT_IDS = tuple(c.strip() for c in os.environ.get("GOOGLE_CLIENT_IDS", "").split(",") if c.strip())
    GOOGLE_SERVER_CLIENT_ID = os.environ.get("GOOGLE_SERVER_CLIENT_ID", "")
    # The monthly money staff credit to a verified household or business: the dashboard fills these in
    # and staff can change each one. Demo values: agree the real ones with the municipality.
    HOUSEHOLD_MONTHLY_IQD = _int("HOUSEHOLD_MONTHLY_IQD", 10000)
    BUSINESS_MONTHLY_IQD = _int("BUSINESS_MONTHLY_IQD", 25000)
    MAX_MONTHLY_IQD = _int("MAX_MONTHLY_IQD", 1000000)      # a typo with extra zeros is refused
    # Households and businesses must be inside this box (min_lat,min_lon,max_lat,max_lon): roughly
    # Sulaimani governorate, so a pin dropped in the sea or a simulator's Cupertino is caught.
    SERVICE_AREA_BBOX = tuple(float(v) for v in os.environ.get("SERVICE_AREA_BBOX", "34.3,44.3,36.6,46.4").split(","))

    # AI
    # "yolo" for real use; "colorblob" counts red paper as litter (rehearsal without a model)
    DETECTOR_KIND = os.environ.get("DETECTOR_KIND", "yolo")
    MODEL_PATH = os.environ.get("MODEL_PATH", str(BASE_DIR / "models" / "yolov8n.pt"))
    # Comma-separated class names that count as litter. "*" = every class (use with a trash model).
    LITTER_CLASSES = os.environ.get(
        "LITTER_CLASSES",
        "bottle,cup,wine glass,bowl,fork,knife,spoon,banana,apple,orange,sandwich,pizza,donut",
    )
    DETECT_CONFIDENCE = _float("DETECT_CONFIDENCE", 0.25)
    # Synthetic pictures for phone simulators that have no camera (app/simulator.py). Rehearsal only.
    SIM_CAMERA = os.environ.get("SIM_CAMERA", "1" if DETECTOR_KIND == "colorblob" else "0") == "1"

    # Verification chain (tune on site)
    CHALLENGE_MINUTES = _int("CHALLENGE_MINUTES", 5)
    CLEANUP_RADIUS_M = _int("CLEANUP_RADIUS_M", 50)
    CONFIRM_RADIUS_M = _float("CONFIRM_RADIUS_M", 5.0)
    HASH_MAX_DISTANCE = _int("HASH_MAX_DISTANCE", 6)       # pHash bits; <= this = same image
    SAME_PLACE_MIN_INLIERS = _int("SAME_PLACE_MIN_INLIERS", 20)
    LITTER_DROP_VERIFIED = _float("LITTER_DROP_VERIFIED", 0.8)
    LITTER_DROP_REVIEW = _float("LITTER_DROP_REVIEW", 0.5)
    MIN_FRAMES = _int("MIN_FRAMES", 4)
    MAX_FRAMES = _int("MAX_FRAMES", 16)
    QR_PREFIX = os.environ.get("QR_PREFIX", "GL-BIN")
    # Dirtiness: a litter count up to each limit gives level 1, 2, 3, 4; above the last is 5.
    # Tune on day two with tools/evaluate.py --suggest-bands on the 50 Slemani test photos.
    LEVEL_COUNT_BANDS = tuple(int(v) for v in os.environ.get("LEVEL_COUNT_BANDS", "2,5,10,20").split(","))

    # Points (starting values from the build plan)
    REPORT_POINTS = {1: 5, 2: 8, 3: 11, 4: 15, 5: 20}
    CLEANUP_POINTS = {1: 20, 2: 40, 3: 60, 4: 80, 5: 100}
    CONFIRMATION_POINTS = _int("CONFIRMATION_POINTS", 2)
    DAILY_REWARDED_REPORTS = _int("DAILY_REWARDED_REPORTS", 5)
    HOLD_HOURS = _int("HOLD_HOURS", 24)
    IMMEDIATE_SHARE = _float("IMMEDIATE_SHARE", 0.2)
    SELF_CLEANUP_BLOCK_HOURS = _int("SELF_CLEANUP_BLOCK_HOURS", 24)
    # Daily tasks: code -> (how many today, bonus points). The bonus is held HOLD_HOURS like the
    # rest and stays below a cleanup's points, so tasks never pay more than the work itself.
    DAILY_TASKS = {"report": (1, 3), "confirm": (1, 2), "cleanup": (1, 10)}
    # Points shop: reward code -> cost in released points. Names are in strings.py. These are
    # demo rewards; agree the real ones (and who honours the vouchers) with the municipality.
    REWARDS = {"cloth_bag": 40, "bus_ticket": 50, "park_coffee": 80, "tree": 150}
    # Trust score: how each outcome moves the person's users.trust_level. Shown to reviewers.
    TRUST_DELTAS = {"verified": 1, "approved_by_staff": 1, "report_confirmed": 1,
                    "rejected_by_staff": -2, "reused_media": -2, "static_frames": -1,
                    "instruction_not_followed": -1}

    # Kurdish description of each report photo. A template sentence is always written (works with
    # no internet); with DESCRIBE_WITH_CLAUDE=1 and an Anthropic API key, a vision model rewrites it
    # in the background. Photos then leave the laptop, so keep it off unless that is agreed.
    DESCRIBE_WITH_CLAUDE = os.environ.get("DESCRIBE_WITH_CLAUDE", "0") == "1"
    DESCRIBE_MODEL = os.environ.get("DESCRIBE_MODEL", "claude-opus-5-5")
    DESCRIBE_TIMEOUT = _float("DESCRIBE_TIMEOUT", 30)

    # Map centre for clients
    MAP_CENTER = (35.5613, 45.4373)   # Slemani (lat, lon)
