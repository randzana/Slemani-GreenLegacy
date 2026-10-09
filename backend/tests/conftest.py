import io
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app                       # noqa: E402
from app.ai.detector import ColorBlobDetector    # noqa: E402
from app.otp import FakeOtpSender                # noqa: E402
from seed import seed                            # noqa: E402
from tools import synthetic                      # noqa: E402

TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql://gl:gl@localhost:5432/greenlegacy_test")
STAFF = ("07500000000", "staff1234")
SLEMANI = (35.5613, 45.4373)


# Every test request comes from 127.0.0.1, so the per-IP and overall hourly email-code caps would
# stop tests that sign up many people; tests/test_otp.py sets its own caps where it tests them.
TEST_SETTINGS = {"TESTING": True, "OTP_MAX_PER_IP_HOUR": 10_000, "OTP_MAX_PER_HOUR": 10_000}


@pytest.fixture()
def app(tmp_path):
    seed(TEST_DB, *STAFF)
    return create_app({"DATABASE_URL": TEST_DB, "UPLOAD_DIR": str(tmp_path / "uploads"), **TEST_SETTINGS},
                      detector=ColorBlobDetector(), otp_sender=FakeOtpSender())


@pytest.fixture()
def client(app):
    return app.test_client()


class Api:
    """Small helper so tests read like the phone's flow."""

    def __init__(self, client):
        self.client = client
        self._phone = 7700000000

    def signup(self, name="هاوڵاتی", neighbourhood_id=1):
        self._phone += 1
        r = self.client.post("/auth/signup", json={"name": name, "phone": f"0{self._phone}",
                                                   "password": "secret123",
                                                   "neighbourhood_id": neighbourhood_id})
        assert r.status_code == 201, r.json
        return {"Authorization": f"Bearer {r.json['token']}"}

    def staff(self):
        r = self.client.post("/auth/login", json={"phone": STAFF[0], "password": STAFF[1]})
        return {"Authorization": f"Bearer {r.json['token']}"}

    def report(self, headers, image, lat=SLEMANI[0], lon=SLEMANI[1]):
        data = {"lat": str(lat), "lon": str(lon),
                "photo": (io.BytesIO(synthetic.encode(image)), "photo.jpg")}
        return self.client.post("/reports", data=data, headers=headers,
                                content_type="multipart/form-data")

    def claim(self, headers, report_id):
        return self.client.post(f"/reports/{report_id}/claim", headers=headers)

    def cleanup(self, headers, report_id, challenge_id, frames, lat=SLEMANI[0], lon=SLEMANI[1]):
        data = {"lat": str(lat), "lon": str(lon), "challenge_id": str(challenge_id),
                "frames": [(io.BytesIO(synthetic.encode(f)), f"f{i}.jpg") for i, f in enumerate(frames)]}
        return self.client.post(f"/reports/{report_id}/cleanup", data=data, headers=headers,
                                content_type="multipart/form-data")

    def me(self, headers):
        return self.client.get("/me", headers=headers).json


@pytest.fixture()
def api(client):
    return Api(client)
