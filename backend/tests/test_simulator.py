"""The stand-in camera for phone simulators: its pictures must pass the real verification chain."""
import cv2
import numpy as np
import pytest

from app import create_app
from app.ai.detector import ColorBlobDetector
from conftest import STAFF, TEST_DB, Api
from seed import seed


def _image(response):
    assert response.status_code == 200, response.data[:200]
    assert response.mimetype == "image/jpeg"
    return cv2.imdecode(np.frombuffer(response.data, np.uint8), cv2.IMREAD_COLOR)


@pytest.fixture()
def sim_client(tmp_path):
    seed(TEST_DB, *STAFF)
    app = create_app({"DATABASE_URL": TEST_DB, "UPLOAD_DIR": str(tmp_path / "uploads"),
                      "TESTING": True, "SIM_CAMERA": True}, detector=ColorBlobDetector())
    return app.test_client()


def test_simulated_camera_completes_the_loop(sim_client):
    api = Api(sim_client)
    reporter, cleaner = api.signup("ڕاپۆرتکەر"), api.signup("پاککەرەوە")

    r = api.report(reporter, _image(sim_client.get("/sim/report-photo")))
    assert r.status_code == 201, r.json
    report_id = r.json["report"]["id"]
    assert r.json["report"]["litter_count"] >= 3

    ch = api.claim(cleaner, report_id).json
    frames = [_image(sim_client.get(f"/sim/cleanup-frame?report_id={report_id}"
                                    f"&instruction={ch['instruction']}&frame={i}&count=8"))
              for i in range(8)]
    result = api.cleanup(cleaner, report_id, ch["id"], frames)
    assert result.json["verdict"] == "verified", result.json


def test_simulated_camera_is_off_by_default(client):
    assert client.get("/sim/report-photo").status_code == 404
