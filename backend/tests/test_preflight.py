"""tools/preflight.py: what it says about a ready database, an old one, a running server and the
settings that must never reach the stage."""
import threading
from pathlib import Path

import psycopg
import pytest
from werkzeug.serving import make_server

from app import create_app
from app.ai.detector import ColorBlobDetector
from conftest import STAFF, TEST_DB
from seed import seed
from tools import preflight
from tools.preflight import FAIL, OK, WARN

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
# what the demo laptop has: the model and staff password from .env, not the public defaults
TERMINAL = {"MODEL_PATH": "models/slemani.pt"}
STAFF_PASSWORD = "from-the-env-file"
STAFF_PHONE = "+9647500000000"     # seed.py stores STAFF[0] in E.164 (app/phones.py)


def marks(results):
    return {label: (mark, detail) for mark, label, detail in results}


def run_sql(sql):
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        conn.execute(sql)


@pytest.fixture()
def db():
    seed(TEST_DB, STAFF[0], STAFF_PASSWORD)
    yield TEST_DB
    seed(TEST_DB, *STAFF)       # some tests break the schema on purpose


def test_seeded_database_is_ready(db):
    results = preflight.check_database(db)
    assert {mark for mark, _, _ in results} == {OK}
    found = marks(results)
    assert STAFF_PHONE in found["هەژماری شارەوانی"][1]
    assert found["گەڕەکەکان"][1].startswith("6 neighbourhoods")


def test_database_from_the_first_schema_names_the_migrations(db):
    """The first schema.sql had no reports.description(_source), point_ledger.detail or .honoured_at."""
    run_sql("ALTER TABLE reports DROP COLUMN description, DROP COLUMN description_source;"
            "ALTER TABLE point_ledger DROP COLUMN detail, DROP COLUMN honoured_at")
    mark, detail = marks(preflight.check_database(db))["ستوونە نوێکان"]
    assert mark == FAIL
    assert "reports.description" in detail and "point_ledger.detail" in detail and "honoured_at" in detail
    assert detail.count("migrations/001_shop_tasks_description.sql") == 1
    assert detail.index("001_shop_tasks_description.sql") < detail.index("003_voucher_honoured.sql")

    # and running the named files really is the fix
    for name in ("001_shop_tasks_description.sql", "003_voucher_honoured.sql"):
        run_sql((MIGRATIONS / name).read_text(encoding="utf-8"))
    assert {mark for mark, _, _ in preflight.check_database(db)} == {OK}


def test_database_from_before_vouchers_could_be_handed_over_names_migration_003(db):
    run_sql("ALTER TABLE point_ledger DROP COLUMN honoured_at")
    mark, detail = marks(preflight.check_database(db))["ستوونە نوێکان"]
    assert mark == FAIL and "point_ledger.honoured_at" in detail
    assert "migrations/003_voucher_honoured.sql" in detail and "001" not in detail
    run_sql((MIGRATIONS / "003_voucher_honoured.sql").read_text(encoding="utf-8"))
    assert marks(preflight.check_database(db))["ستوونە نوێکان"][0] == OK


def test_database_from_before_pins_and_bins_names_migrations_004_to_006(db):
    """Map pins (004, 005) and trash bins (006) came later; 001 had rewritten the ledger's kind check
    without 'bin_disposal'. Running the named files, even twice, is the fix."""
    run_sql("DROP TABLE bin_disposals, trash_bins, pin_registrations, notifications, pins;"
            "ALTER TABLE point_ledger DROP COLUMN bin_id;"
            "ALTER TABLE point_ledger DROP CONSTRAINT point_ledger_kind_check;"
            "ALTER TABLE point_ledger ADD CONSTRAINT point_ledger_kind_check"
            "    CHECK (kind IN ('report', 'confirmation', 'cleanup', 'task', 'redeem'))")
    found = marks(preflight.check_database(db))
    mark, detail = found["خشتە نوێکان"]
    assert mark == FAIL and "pins" in detail and "trash_bins" in detail and "bin_disposals" in detail
    assert detail.index("004_custom_pins") < detail.index("005_pin_registrations") < detail.index("006_trash_bins")
    assert found["ستوونە نوێکان"][0] == FAIL and "point_ledger.bin_id" in found["ستوونە نوێکان"][1]

    for _ in range(2):
        for name in ("004_custom_pins_and_notifications.sql", "005_pin_registrations.sql", "006_trash_bins.sql"):
            run_sql((MIGRATIONS / name).read_text(encoding="utf-8"))
    assert {mark for mark, _, _ in preflight.check_database(db)} == {OK}
    run_sql("""INSERT INTO point_ledger (user_id, amount, kind, status)
               SELECT id, 15, 'bin_disposal', 'released' FROM users LIMIT 1""")


def test_public_default_staff_password_warns(db):
    """seed.py without STAFF_PASSWORD: the password is in the README."""
    assert marks(preflight.check_database(db))["وشەی نهێنیی شارەوانی"][0] == OK
    seed(db, *STAFF)
    mark, detail = marks(preflight.check_database(db))["وشەی نهێنیی شارەوانی"]
    assert mark == WARN and STAFF_PHONE in detail and "STAFF_PASSWORD" in detail


def test_polygon_boundaries_name_migration_002(db):
    run_sql("ALTER TABLE neighbourhoods ALTER COLUMN boundary TYPE GEOGRAPHY(POLYGON, 4326)")
    mark, detail = marks(preflight.check_database(db))["سنووری گەڕەکەکان"]
    assert mark == WARN and "migrations/002_neighbourhood_boundaries.sql" in detail
    run_sql((MIGRATIONS / "002_neighbourhood_boundaries.sql").read_text(encoding="utf-8"))
    assert "سنووری گەڕەکەکان" not in marks(preflight.check_database(db))


def test_empty_or_unseeded_database_says_seed(db):
    run_sql("DELETE FROM users; DELETE FROM neighbourhoods")
    found = marks(preflight.check_database(db))
    assert found["هەژماری شارەوانی"][0] == FAIL and found["گەڕەکەکان"][0] == FAIL
    run_sql("DROP TABLE point_ledger, cleanups CASCADE")
    mark, detail = marks(preflight.check_database(db))["خشتەکان"]
    assert mark == FAIL and "cleanups" in detail and "point_ledger" in detail and "seed.py" in detail


def test_unreachable_database_is_one_clear_line(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    results = preflight.check_database("postgresql://gl:secret@localhost:1/nothing")
    assert len(results) == 1 and results[0][0] == FAIL
    assert "localhost:1/nothing" in results[0][2] and "secret" not in results[0][2]
    assert "DATABASE_URL is not set" in results[0][2] and "5433" not in results[0][2]


def test_uploads_folder_must_be_writable(tmp_path):
    found = marks(preflight.check_uploads(tmp_path / "uploads"))
    assert found["فۆڵدەری وێنەکان"][0] == OK and "MB free" in found["شوێنی بەتاڵی دیسک"][1]
    (tmp_path / "a_file").write_text("x")
    assert preflight.check_uploads(tmp_path / "a_file" / "uploads")[0][0] == FAIL


def detector_cfg(**changes):
    cfg = {"DETECTOR_KIND": "yolo", "MODEL_PATH": "/nowhere/slemani.pt", "LITTER_CLASSES": "*",
           "DETECT_CONFIDENCE": 0.25}
    cfg.update(changes)
    return cfg


def test_colorblob_fails_unless_rehearsal():
    assert marks(preflight.check_detector(detector_cfg(DETECTOR_KIND="colorblob")))["ناسەری پاشماوە"][0] == FAIL
    rehearsal = marks(preflight.check_detector(detector_cfg(DETECTOR_KIND="colorblob"), rehearsal=True))
    assert rehearsal["ناسەری پاشماوە"][0] == WARN
    assert rehearsal["فایلی مۆدێل"][0] == WARN        # not used by colorblob, but needed on stage


def test_model_file(tmp_path):
    assert marks(preflight.check_detector(detector_cfg()))["فایلی مۆدێل"][0] == FAIL
    model = tmp_path / "slemani.pt"
    model.write_bytes(b"\0" * 1024)
    assert marks(preflight.check_detector(detector_cfg(MODEL_PATH=str(model))))["فایلی مۆدێل"][0] == OK
    stock = tmp_path / "yolov8n.pt"
    stock.write_bytes(b"\0")
    assert marks(preflight.check_detector(detector_cfg(MODEL_PATH=str(stock))))["فایلی مۆدێل"][0] == FAIL
    assert marks(preflight.check_detector(
        detector_cfg(MODEL_PATH=str(stock), LITTER_CLASSES="bottle,cup")))["فایلی مۆدێل"][0] == WARN


def test_settings_that_must_not_reach_the_stage(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = {"SIM_CAMERA": True, "DESCRIBE_WITH_CLAUDE": True}
    found = marks(preflight.check_settings(cfg))
    assert found["کامێرای ساختە"][0] == FAIL
    assert found["کلیلی نهێنی"][0] == WARN and found["وەسفی Claude"][0] == WARN
    assert marks(preflight.check_settings(cfg, rehearsal=True))["کامێرای ساختە"][0] == WARN
    monkeypatch.setenv("SECRET_KEY", "a-long-random-value")
    found = marks(preflight.check_settings({"SIM_CAMERA": False, "DESCRIBE_WITH_CLAUDE": False}))
    assert {mark for mark, _ in found.values()} == {OK}


def test_phone_url_uses_the_port():
    results = preflight.check_network(5101)
    if results[0][0] == OK:          # a machine with no network at all only gets a warning
        assert ":5101" in marks(results)["ناونیشان بۆ مۆبایلەکان"][1]


@pytest.fixture()
def server(db, tmp_path):
    """A real HTTP server on a free port, so the check goes through requests like on the laptop."""
    started = []

    def start(sim_camera=False, model="slemani.pt", database=db):
        # MODEL_PATH only names the model in /health here: the detector is passed in
        app = create_app({"DATABASE_URL": database, "UPLOAD_DIR": str(tmp_path), "SIM_CAMERA": sim_camera,
                          "MODEL_PATH": f"/laptop/backend/models/{model}"}, detector=ColorBlobDetector())
        httpd = make_server("127.0.0.1", 0, app, threaded=True)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started.append(httpd)
        return f"http://127.0.0.1:{httpd.port}"
    yield start
    for httpd in started:
        httpd.shutdown()


def test_running_server(server):
    found = marks(preflight.check_server(server(sim_camera=False), TERMINAL))
    assert {mark for mark, _ in found.values()} == {OK}
    assert found["مۆدێلی سێرڤەر"][1] == "slemani.pt" and "6 neighbourhoods" in found["داتابەیسی سێرڤەر"][1]
    url = server(sim_camera=True)
    assert marks(preflight.check_server(url, TERMINAL))["کامێرای ساختە (سێرڤەر)"][0] == FAIL
    assert marks(preflight.check_server(url + "/", TERMINAL, rehearsal=True))["کامێرای ساختە (سێرڤەر)"][0] == WARN
    assert preflight.check_server("http://127.0.0.1:1", TERMINAL)[0][0] == FAIL


def test_server_runs_another_model_than_this_terminal_checked(server):
    """The server was started in a window without the .env: every model check of this terminal
    was about a file the stage never uses."""
    mark, detail = marks(preflight.check_server(server(model="yolov8m-seg.pt"), TERMINAL))["مۆدێلی سێرڤەر"]
    assert mark == FAIL and "yolov8m-seg.pt" in detail and "slemani.pt" in detail
    stock = marks(preflight.check_server(server(model="yolov8n.pt"), {"MODEL_PATH": "models/yolov8n.pt"}))
    assert stock["مۆدێلی سێرڤەر"][0] == WARN


def test_server_without_its_database(server):
    """/health answers without a database, but the phones could not even sign up."""
    found = marks(preflight.check_server(server(database="postgresql://gl:gl@localhost:1/nothing"), TERMINAL))
    assert found["سێرڤەر"][0] == OK
    assert found["داتابەیسی سێرڤەر"][0] == FAIL and "/neighbourhoods 500" in found["داتابەیسی سێرڤەر"][1]
    run_sql("DELETE FROM users; DELETE FROM neighbourhoods")
    assert marks(preflight.check_server(server(), TERMINAL))["داتابەیسی سێرڤەر"][0] == FAIL


def test_exit_code(db, server, tmp_path, monkeypatch, capsys):
    cfg = dict(preflight.settings(), DATABASE_URL=db, UPLOAD_DIR=str(tmp_path), DETECTOR_KIND="colorblob",
               SIM_CAMERA=True, DESCRIBE_WITH_CLAUDE=False, MODEL_PATH="models/slemani.pt")
    monkeypatch.setattr(preflight, "settings", lambda: cfg)
    assert preflight.main(["--rehearsal"]) == 0
    assert preflight.main([]) == 1
    assert "colorblob" in capsys.readouterr().out
    # main hands this terminal's settings to the server check
    assert preflight.main(["--rehearsal", "--server", server()]) == 0
    assert preflight.main(["--rehearsal", "--server", server(model="yolov8m-seg.pt")]) == 1
    assert "the running server uses yolov8m-seg.pt" in capsys.readouterr().out
