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


def marks(results):
    return {label: (mark, detail) for mark, label, detail in results}


def run_sql(sql):
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        conn.execute(sql)


@pytest.fixture()
def db():
    seed(TEST_DB, *STAFF)
    yield TEST_DB
    seed(TEST_DB, *STAFF)       # some tests break the schema on purpose


def test_seeded_database_is_ready(db):
    results = preflight.check_database(db)
    assert {mark for mark, _, _ in results} == {OK}
    found = marks(results)
    assert STAFF[0] in found["هەژماری شارەوانی"][1]
    assert found["گەڕەکەکان"][1].startswith("6 neighbourhoods")


def test_database_from_the_first_schema_names_the_migration(db):
    """The first schema.sql had no reports.description(_source) or point_ledger.detail."""
    run_sql("ALTER TABLE reports DROP COLUMN description, DROP COLUMN description_source;"
            "ALTER TABLE point_ledger DROP COLUMN detail")
    mark, detail = marks(preflight.check_database(db))["ستوونە نوێکان"]
    assert mark == FAIL
    assert "reports.description" in detail and "point_ledger.detail" in detail
    assert detail.count("migrations/001_shop_tasks_description.sql") == 1

    # and running the named file really is the fix
    run_sql((MIGRATIONS / "001_shop_tasks_description.sql").read_text(encoding="utf-8"))
    assert {mark for mark, _, _ in preflight.check_database(db)} == {OK}


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


def test_unreachable_database_is_one_clear_line():
    results = preflight.check_database("postgresql://gl:secret@localhost:1/nothing")
    assert len(results) == 1 and results[0][0] == FAIL
    assert "localhost:1/nothing" in results[0][2] and "secret" not in results[0][2]


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

    def start(sim_camera):
        app = create_app({"DATABASE_URL": db, "UPLOAD_DIR": str(tmp_path), "SIM_CAMERA": sim_camera},
                         detector=ColorBlobDetector())
        httpd = make_server("127.0.0.1", 0, app, threaded=True)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started.append(httpd)
        return f"http://127.0.0.1:{httpd.port}"
    yield start
    for httpd in started:
        httpd.shutdown()


def test_running_server(server):
    found = marks(preflight.check_server(server(sim_camera=False)))
    assert {mark for mark, _ in found.values()} == {OK}
    url = server(sim_camera=True)
    assert marks(preflight.check_server(url))["کامێرای ساختە (سێرڤەر)"][0] == FAIL
    assert marks(preflight.check_server(url + "/", rehearsal=True))["کامێرای ساختە (سێرڤەر)"][0] == WARN
    assert preflight.check_server("http://127.0.0.1:1")[0][0] == FAIL


def test_exit_code(db, tmp_path, monkeypatch, capsys):
    cfg = dict(preflight.settings(), DATABASE_URL=db, UPLOAD_DIR=str(tmp_path), DETECTOR_KIND="colorblob",
               SIM_CAMERA=True, DESCRIBE_WITH_CLAUDE=False)
    monkeypatch.setattr(preflight, "settings", lambda: cfg)
    assert preflight.main(["--rehearsal"]) == 0
    assert preflight.main([]) == 1
    assert "colorblob" in capsys.readouterr().out
