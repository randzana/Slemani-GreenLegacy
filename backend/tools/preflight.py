"""Preflight: run on the demo laptop before going on stage, in the same terminal setup as the server.

    cd backend
    MODEL_PATH=models/yolov8m-seg.pt LITTER_CLASSES=* python tools/preflight.py --model --server http://localhost:5000
    DETECTOR_KIND=colorblob python tools/preflight.py --rehearsal --server http://localhost:5000

One line per check: ✓ fine, ⚠ look at it, ✗ fix it before the demo (the exit code is then 1).
Settings come from the environment through app.config, so give it the same variables as run.py.
"""
import argparse
import importlib.util
import os
import shutil
import socket
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import psycopg
import requests
from werkzeug.security import check_password_hash

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.config import Config  # noqa: E402
from seed import DEFAULT_STAFF_PASSWORD  # noqa: E402

OK, WARN, FAIL = "✓", "⚠", "✗"
TABLES = ("neighbourhoods", "users", "reports", "challenges", "cleanups", "point_ledger")
# Columns added after the first schema.sql, and the migration that adds them without losing data
NEWER_COLUMNS = {("reports", "description"): "001_shop_tasks_description.sql",
                 ("reports", "description_source"): "001_shop_tasks_description.sql",
                 ("point_ledger", "detail"): "001_shop_tasks_description.sql",
                 ("point_ledger", "honoured_at"): "003_voucher_honoured.sql",
                 ("point_ledger", "bin_id"): "006_trash_bins.sql",
                 ("users", "email"): "007_accounts_email_google.sql",
                 ("users", "email_key"): "007_accounts_email_google.sql",
                 ("users", "email_verified_at"): "007_accounts_email_google.sql"}
# Tables added after the first schema.sql, and the migration that creates them
NEWER_TABLES = {"pins": "004_custom_pins_and_notifications.sql",
                "notifications": "004_custom_pins_and_notifications.sql",
                "pin_registrations": "005_pin_registrations.sql",
                "trash_bins": "006_trash_bins.sql", "bin_disposals": "006_trash_bins.sql",
                "user_identities": "007_accounts_email_google.sql", "places": "007_accounts_email_google.sql",
                "place_reviews": "007_accounts_email_google.sql", "place_payments": "007_accounts_email_google.sql",
                "otp_codes": "007_accounts_email_google.sql"}
STOCK_MODEL = "yolov8n.pt"
MIN_FREE_MB, LOW_FREE_MB = 200, 1000    # a report photo plus an 8-frame video is a few MB


def settings():
    return {name: value for name, value in vars(Config).items() if name.isupper()}


def migrate(files):
    return " then ".join(f'psql "$DATABASE_URL" -f migrations/{name}' for name in sorted(set(files)))


def check_database(url):
    """Connection, PostGIS, the six tables, newer columns and tables, staff account and neighbourhoods."""
    where = url.rsplit("@", 1)[-1]          # host:port/name, without the password
    try:
        conn = psycopg.connect(url, connect_timeout=5, autocommit=True)
    except psycopg.Error as exc:
        hint = "" if "DATABASE_URL" in os.environ else (" (DATABASE_URL is not set: source .env, or export it "
                                                        "if your PostgreSQL uses another port or database)")
        return [(FAIL, "داتابەیس", f"cannot connect to {where}: {str(exc).strip().splitlines()[0]}{hint}")]
    with conn:
        out = [(OK, "داتابەیس", where)]
        postgis = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'postgis'").fetchone()
        if not postgis:
            return out + [(FAIL, "PostGIS", "extension missing: CREATE EXTENSION postgis; as a superuser")]
        out.append((OK, "PostGIS", postgis[0]))

        columns = set(conn.execute("""SELECT table_name, column_name FROM information_schema.columns
                                      WHERE table_schema = current_schema()""").fetchall())
        tables = {table for table, _ in columns}
        missing = [t for t in TABLES if t not in tables]
        if missing:
            return out + [(FAIL, "خشتەکان", f"missing {', '.join(missing)}: python seed.py (wipes the database)")]
        out.append((OK, "خشتەکان", "all six tables"))
        old = [col for col in NEWER_COLUMNS if col not in columns]
        if old:
            names = ", ".join(".".join(col) for col in old)
            out.append((FAIL, "ستوونە نوێکان", f"missing {names}: {migrate(NEWER_COLUMNS[c] for c in old)}"))
        else:
            out.append((OK, "ستوونە نوێکان", f"all {len(NEWER_COLUMNS)}, up to {max(NEWER_COLUMNS.values())}"))
        absent = [t for t in NEWER_TABLES if t not in tables]
        out.append((FAIL, "خشتە نوێکان", f"missing {', '.join(absent)}: {migrate(NEWER_TABLES[t] for t in absent)}")
                   if absent else (OK, "خشتە نوێکان", f"all {len(NEWER_TABLES)}, up to {max(NEWER_TABLES.values())}"))
        shape = conn.execute("""SELECT type FROM geography_columns
                                WHERE f_table_schema = current_schema() AND f_table_name = 'neighbourhoods'
                                  AND f_geography_column = 'boundary'""").fetchone()
        if shape and shape[0] != "MultiPolygon":     # only tools/import_boundaries.py needs it
            out.append((WARN, "سنووری گەڕەکەکان", f"boundary is {shape[0]}: "
                                                   f"{migrate(['002_neighbourhood_boundaries.sql'])}"))

        staff = conn.execute("SELECT phone, password_hash FROM users WHERE role = 'staff' ORDER BY id").fetchall()
        out.append((OK, "هەژماری شارەوانی", ", ".join(phone for phone, _ in staff)) if staff else
                   (FAIL, "هەژماری شارەوانی", "no staff account: python seed.py (wipes the database)"))
        # seed.py's fallback is printed in the README: anyone who read it could approve cleanups on stage
        public = [phone for phone, hashed in staff if check_password_hash(hashed, DEFAULT_STAFF_PASSWORD)]
        if public:
            out.append((WARN, "وشەی نهێنیی شارەوانی",
                        f"{', '.join(public)} still has the public password {DEFAULT_STAFF_PASSWORD}: put "
                        "STAFF_PASSWORD in .env (docs/DEMO.md), then python seed.py (wipes the database)"))
        elif staff:
            out.append((OK, "وشەی نهێنیی شارەوانی", "not the default"))
        hoods, with_area = conn.execute("SELECT count(*), count(boundary) FROM neighbourhoods").fetchone()
        out.append((OK, "گەڕەکەکان", f"{hoods} neighbourhoods, {with_area} with a boundary") if hoods else
                   (FAIL, "گەڕەکەکان", "none: python seed.py (wipes the database)"))
    return out


def check_uploads(upload_dir):
    folder = Path(upload_dir)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=folder):
            pass
    except OSError as exc:
        return [(FAIL, "فۆڵدەری وێنەکان", f"{folder} is not writable: {exc.strerror}")]
    free_mb = shutil.disk_usage(folder).free // 2**20
    mark = FAIL if free_mb < MIN_FREE_MB else WARN if free_mb < LOW_FREE_MB else OK
    return [(OK, "فۆڵدەری وێنەکان", str(folder)), (mark, "شوێنی بەتاڵی دیسک", f"{free_mb} MB free")]


def check_detector(cfg, rehearsal=False, load=False):
    """The detector the server will use. Never colorblob on stage: it counts red paper, not litter."""
    yolo = cfg["DETECTOR_KIND"] != "colorblob"
    classes = cfg["LITTER_CLASSES"] if len(cfg["LITTER_CLASSES"]) <= 30 else cfg["LITTER_CLASSES"][:27] + "..."
    if yolo:
        out = [(OK, "ناسەری پاشماوە", f"yolo, LITTER_CLASSES={classes}")]
    else:
        out = [(WARN if rehearsal else FAIL, "ناسەری پاشماوە",
                "colorblob counts red paper: rehearsal only, start the server without DETECTOR_KIND")]
    # with colorblob the model is not used now, but it is the one going on stage
    need = FAIL if yolo else WARN
    model = Path(cfg["MODEL_PATH"])
    shown = model.resolve().relative_to(ROOT) if model.resolve().is_relative_to(ROOT) else model
    if not model.is_file():
        out.append((need, "فایلی مۆدێل", f"no file at {shown}: set MODEL_PATH or python tools/download_model.py"))
    elif model.name == STOCK_MODEL and cfg["LITTER_CLASSES"] == "*":
        out.append((need, "فایلی مۆدێل", f"{shown} is the stock COCO model: with LITTER_CLASSES=* people count"))
    elif model.name == STOCK_MODEL:
        out.append((WARN, "فایلی مۆدێل", f"{shown} is the stock COCO model (bottles, cups): the fallback, "
                                          "not the trash or Slemani model"))
    else:
        out.append((OK, "فایلی مۆدێل", f"{shown} ({model.stat().st_size // 2**20} MB)"))
    if importlib.util.find_spec("ultralytics") is None:
        out.append((need, "ultralytics", "not installed: pip install ultralytics"))
    elif load and model.is_file():
        out.append(load_model(cfg))
    return out


def load_model(cfg):
    """Load the model like run.py does and time it, so a broken file or slow laptop shows now."""
    from app.ai.detector import YoloDetector
    from tools import synthetic
    detector = YoloDetector(cfg["MODEL_PATH"], cfg["LITTER_CLASSES"], cfg["DETECT_CONFIDENCE"])
    try:
        start = time.perf_counter()
        detector.warm_up()
        warm = time.perf_counter() - start
        start = time.perf_counter()
        detector.detect(synthetic.place(1))       # YOLO resizes every photo to 640 px anyway
        photo = time.perf_counter() - start
    except Exception as exc:   # a missing package, a pickle from another version, wrong classes...
        return (FAIL, "بارکردنی مۆدێل", f"{type(exc).__name__}: {exc}")
    if detector.litter is None and "person" in detector._model.names.values():
        return (FAIL, "بارکردنی مۆدێل", "a COCO model with LITTER_CLASSES=*: people would count as litter")
    return (OK, "بارکردنی مۆدێل", f"loaded and warmed up in {warm:.1f} s, then {photo * 1000:.0f} ms per photo")


def check_files():
    leaflet = ROOT / "app" / "static" / "leaflet"
    gone = [name for name in ("leaflet.js", "leaflet.css") if not (leaflet / name).is_file()]
    stickers = ROOT / "qr_stickers.png"
    return [(FAIL, "Leaflet", f"missing {', '.join(gone)} in {leaflet}: the dashboard map will not load")
            if gone else (OK, "Leaflet", "app/static/leaflet (works without internet)"),
            (OK, "ستیکەری QR", "qr_stickers.png") if stickers.is_file() else
            (WARN, "ستیکەری QR", "no qr_stickers.png: python tools/make_qr_stickers.py, then print it")]


def check_settings(cfg, rehearsal=False):
    # the default key is written in config.py, so only the environment can say it was replaced
    out = [(WARN, "کلیلی نهێنی", "SECRET_KEY is the default from the code: export SECRET_KEY=<random>")
           if not os.environ.get("SECRET_KEY") else (OK, "کلیلی نهێنی", "SECRET_KEY set")]
    if cfg["SIM_CAMERA"]:
        out.append((WARN if rehearsal else FAIL, "کامێرای ساختە",
                    "SIM_CAMERA is on: synthetic photos for simulators, never on stage"))
    else:
        out.append((OK, "کامێرای ساختە", "SIM_CAMERA off"))
    if not cfg["DESCRIBE_WITH_CLAUDE"]:
        out.append((OK, "وەسفی Claude", "off: template sentences, no internet needed"))
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        out.append((WARN, "وەسفی Claude", "DESCRIBE_WITH_CLAUDE=1 but no ANTHROPIC_API_KEY: template only"))
    else:
        out.append((OK, "وەسفی Claude", "on: photos go to the Anthropic API and need the hall internet"))
    return out


def lan_addresses():
    """IPv4 addresses the phones can reach. The UDP connect sends nothing: it only asks the system
    which interface it would use, which on a hotspot is the hotspot one."""
    found = set()
    try:
        found.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.254.254.254", 1))
            found.add(s.getsockname()[0])
        except OSError:
            pass
    return sorted(ip for ip in found if not ip.startswith(("127.", "0.")))


def check_network(port):
    ips = lan_addresses()
    if not ips:
        return [(WARN, "IP ی لاپتۆپ", "no network address: join the hotspot first")]
    return [(OK, "IP ی لاپتۆپ", ", ".join(ips)),
            (OK, "ناونیشان بۆ مۆبایلەکان", "  or  ".join(f"http://{ip}:{port}" for ip in ips))]


def check_server(url, cfg, rehearsal=False):
    """The running server: what the phones and the projector will actually talk to. The checks above
    read this terminal's settings; the server has its own, from the terminal it was started in."""
    url = url.rstrip("/")
    try:
        health = requests.get(f"{url}/health", timeout=5)
        hoods = requests.get(f"{url}/neighbourhoods", timeout=5)      # /health does not touch the database
        dashboard = requests.get(f"{url}/dashboard", timeout=5)
        leaflet = requests.get(f"{url}/static/leaflet/leaflet.js", timeout=5)
        sim = requests.get(f"{url}/sim/report-photo", timeout=10)
    except requests.RequestException as exc:
        return [(FAIL, "سێرڤەر", f"{url}: {type(exc).__name__}, is run.py running?")]
    healthy = health.status_code == 200 and health.headers.get("Content-Type") == "application/json"
    out = [(OK if healthy and health.json().get("ok") else FAIL, "سێرڤەر", f"GET /health {health.status_code}")]
    listed = (hoods.json() if hoods.status_code == 200 and hoods.headers.get("Content-Type") == "application/json"
              else None)
    if listed is None:
        out.append((FAIL, "داتابەیسی سێرڤەر", f"GET /neighbourhoods {hoods.status_code}: the server cannot read its "
                                               "database; restart it after source .env (DATABASE_URL)"))
    elif not listed:
        out.append((FAIL, "داتابەیسی سێرڤەر", "the server's database has no neighbourhoods: python seed.py "
                                               "with the server's DATABASE_URL (wipes the database)"))
    else:
        out.append((OK, "داتابەیسی سێرڤەر", f"GET /neighbourhoods 200, {len(listed)} neighbourhoods"))
    out.append((OK if dashboard.status_code == 200 and leaflet.status_code == 200 else FAIL, "داشبۆرد",
                f"GET /dashboard {dashboard.status_code}, leaflet.js {leaflet.status_code}"))
    # the server may have been started with other variables than this terminal has
    info = health.json() if healthy else {}
    if info.get("detector") == "colorblob":
        out.append((WARN if rehearsal else FAIL, "ناسەری سێرڤەر",
                    "the running server counts red paper (colorblob): restart it with the real model"))
    elif info.get("detector"):
        out.append((OK, "ناسەری سێرڤەر", info["detector"]))
    served, checked = info.get("model"), Path(cfg["MODEL_PATH"]).name
    if served and served != checked:
        # every model check above was about this terminal's MODEL_PATH, not the one on stage
        out.append((FAIL, "مۆدێلی سێرڤەر", f"the running server uses {served}, this terminal checked {checked}: "
                                            "start both from the same .env"))
    elif served == STOCK_MODEL:
        out.append((WARN, "مۆدێلی سێرڤەر", f"{served} is the stock COCO model (bottles, cups): the fallback, "
                                            "not the trash or Slemani model"))
    elif served:
        out.append((OK, "مۆدێلی سێرڤەر", served))
    if sim.status_code == 200:
        out.append((WARN if rehearsal else FAIL, "کامێرای ساختە (سێرڤەر)",
                    "the running server serves /sim photos: restart it without colorblob/SIM_CAMERA"))
    else:
        out.append((OK, "کامێرای ساختە (سێرڤەر)", f"GET /sim/report-photo {sim.status_code}"))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rehearsal", action="store_true", help="allow colorblob and SIM_CAMERA (practice only)")
    parser.add_argument("--model", action="store_true", help="load the model and time a warm-up")
    parser.add_argument("--server", help="also test a running server, e.g. http://localhost:5000")
    args = parser.parse_args(argv)
    cfg = settings()
    port = (urlparse(args.server).port or 80) if args.server else int(os.environ.get("PORT", 5000))

    checks = [lambda: check_database(cfg["DATABASE_URL"]), lambda: check_uploads(cfg["UPLOAD_DIR"]),
              lambda: check_detector(cfg, args.rehearsal, args.model), check_files,
              lambda: check_settings(cfg, args.rehearsal), lambda: check_network(port)]
    if args.server:
        checks.append(lambda: check_server(args.server, cfg, args.rehearsal))
    print("GreenLegacy preflight" + (" (rehearsal)" if args.rehearsal else ""))
    counts = {OK: 0, WARN: 0, FAIL: 0}
    for check in checks:
        for mark, label, detail in check():
            counts[mark] += 1
            print(f"  {mark} {label:<24} {detail}", flush=True)
    print(f"\n{counts[OK]} {OK}  {counts[WARN]} {WARN}  {counts[FAIL]} {FAIL}  "
          + ("ئامادە نییە: پێش شانۆ ✗ ەکان چاک بکە" if counts[FAIL] else "ئامادەیە"))
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
