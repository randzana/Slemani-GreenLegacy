"""Points shop, daily tasks, ranks, trust score and the Kurdish photo description."""
import time

import psycopg
import pytest

from app import create_app
from app.ai.describe import template_description
from app.ai.detector import ColorBlobDetector
from app.config import Config
from conftest import STAFF, TEST_DB, Api
from seed import seed
from test_flow import FAR, NEAR, claimed, dirty_spot
from tools import synthetic


def end_holds():
    """Pretend 24 hours passed: every held point is due."""
    with psycopg.connect(TEST_DB) as conn:
        conn.execute("UPDATE point_ledger SET release_at = now() - interval '1 minute' WHERE release_at IS NOT NULL")


def verified_cleanup(api, seed=50, at=None):
    """Someone reports a spot and the returned cleaner cleans it; returns (cleaner headers, result)."""
    at = at or synthetic_spot(seed)
    _reporter, report, scene = dirty_spot(api, seed=seed, at=at)
    cleaner, challenge = claimed(api, report["id"])
    r = api.cleanup(cleaner, report["id"], challenge["id"],
                    synthetic.cleanup_frames(scene, challenge["instruction"]), *at)
    assert r.json["verdict"] == "verified", r.json
    return cleaner, r.json


def synthetic_spot(seed):
    return (35.55 + 0.003 * (seed % 20), 45.43)


# ---------------------------------------------------------------- description

def test_template_description_is_kurdish_and_counts():
    text = template_description({"bottle": 5, "cup": 3}, 8, 3)
    assert text.startswith("٨ پارچە پاشماوە") and "٥ بوتڵ" in text and "٣ کوپ" in text
    assert "پلەی پیسی ٣" in text
    assert "خێرا" in template_description({"trash": 25}, 25, 5)


def test_report_gets_template_description(api):
    _r, report, _s = dirty_spot(api, seed=60)
    assert "پارچە پاشماوە دۆزرایەوە" in report["description"]


class FakeDescriber:
    def __init__(self):
        self.calls = []

    def describe(self, photo, classes, count, level):
        self.calls.append((count, level))
        return "چەند بوتڵێک لە تەنیشت ڕێگاکەن؛ دوو کیسە بهێنن."


def test_vision_description_replaces_the_template(tmp_path):
    seed(TEST_DB, *STAFF)
    describer = FakeDescriber()
    app = create_app({"DATABASE_URL": TEST_DB, "UPLOAD_DIR": str(tmp_path / "uploads"), "TESTING": True},
                     detector=ColorBlobDetector(), describer=describer)
    api = Api(app.test_client())
    citizen = api.signup()
    r = api.report(citizen, synthetic.with_litter(synthetic.place(61), 5))
    assert r.status_code == 201
    report_id = r.json["report"]["id"]
    for _ in range(40):                       # the model runs in a background thread
        spot = app.test_client().get(f"/reports/{report_id}", headers=citizen).json
        if spot["description"] == "چەند بوتڵێک لە تەنیشت ڕێگاکەن؛ دوو کیسە بهێنن.":
            break
        time.sleep(0.1)
    else:
        pytest.fail("the description was never replaced")
    assert describer.calls and describer.calls[0][0] >= 4


def test_level_bands_are_tunable(api, app):
    app.config["LEVEL_COUNT_BANDS"] = (1, 2, 3, 4)
    _r, report, _s = dirty_spot(api, seed=62, litter=6)
    assert report["dirtiness"] == 5


# ---------------------------------------------------------------- ranks + trust

def test_me_has_rank_and_trust(api):
    cleaner, _result = verified_cleanup(api, seed=63)
    loner = api.signup("هێمن", neighbourhood_id=3)
    me = api.me(cleaner)
    assert me["rank"] == 1 and me["neighbourhood_rank"] == 1
    assert me["citizens"] >= 3 and me["neighbourhoods"] == 6
    assert me["trust_level"] == 1                                 # one verified cleanup
    other = api.me(loner)
    assert other["rank"] > 1 and other["neighbourhood_rank"] > 1
    assert api.me(api.staff())["rank"] is None                    # staff are not in the league


def test_trust_drops_for_reused_media_and_staff_rejection(api, client):
    _rep, report, scene = dirty_spot(api, seed=64)
    cleaner, challenge = claimed(api, report["id"])
    frames = synthetic.cleanup_frames(scene, challenge["instruction"])
    assert api.cleanup(cleaner, report["id"], challenge["id"], frames).json["verdict"] == "verified"

    _r2, report2, _s2 = dirty_spot(api, seed=65, at=FAR)
    challenge2 = api.claim(cleaner, report2["id"]).json
    r = api.cleanup(cleaner, report2["id"], challenge2["id"], frames, *FAR)
    assert r.json["reason_code"] == "reused_media"
    assert api.me(cleaner)["trust_level"] == 1 - 2

    challenge3 = api.claim(cleaner, report2["id"]).json
    r = api.cleanup(cleaner, report2["id"], challenge3["id"],
                    synthetic.cleanup_frames(synthetic.place(66), challenge3["instruction"]), *FAR)
    assert r.json["verdict"] == "review"
    staff = api.staff()
    queue = client.get("/admin/cleanups?verdict=review", headers=staff).json
    assert queue[0]["cleaner_trust"] == -1
    client.post(f"/admin/cleanups/{r.json['cleanup_id']}/review", json={"decision": "reject"}, headers=staff)
    assert api.me(cleaner)["trust_level"] == -3


def test_confirmation_raises_the_reporters_trust(api):
    reporter, report, scene = dirty_spot(api, seed=67)
    confirmer = api.signup()
    api.report(confirmer, synthetic.view(synthetic.with_litter(scene, 6, 98), 3), *NEAR)
    assert api.me(reporter)["trust_level"] == 1


# ---------------------------------------------------------------- points shop

def test_shop_needs_released_points(api, client):
    citizen = api.signup()
    shop = client.get("/rewards", headers=citizen).json
    assert shop["balance"] == 0 and len(shop["rewards"]) == 4
    assert [r["cost"] for r in shop["rewards"]] == sorted(r["cost"] for r in shop["rewards"])
    r = client.post("/rewards/cloth_bag/redeem", headers=citizen)
    assert r.status_code == 409 and r.json["error"] == "not_enough_points"
    assert client.post("/rewards/gold_bar/redeem", headers=citizen).status_code == 404


def test_redeem_spends_points_but_not_rank(api, client, app):
    cleaner, result = verified_cleanup(api, seed=68)
    end_holds()
    before = api.me(cleaner)
    total = before["released"]
    assert total == result["points_now"] + result["points_pending"]
    app.config["REWARDS"] = {**app.config["REWARDS"], "cloth_bag": total}   # costs exactly the balance

    r = client.post("/rewards/cloth_bag/redeem", headers=cleaner)
    assert r.status_code == 201 and r.json["voucher"].startswith("GL-") and r.json["balance"] == 0
    assert api.me(cleaner)["released"] == 0
    again = client.post("/rewards/cloth_bag/redeem", headers=cleaner)   # the same points cannot be spent twice
    assert again.status_code == 409

    board = client.get("/leaderboard", headers=cleaner).json
    assert board["citizens"][0]["points"] == total                       # spending keeps your league place
    assert client.get("/rewards", headers=cleaner).json["vouchers"][0]["voucher"] == r.json["voucher"]

    staff = api.staff()
    listed = client.get("/admin/redemptions", headers=staff).json
    assert listed[0]["voucher"] == r.json["voucher"] and listed[0]["reward"] == "cloth_bag"
    assert client.get("/admin/redemptions", headers=cleaner).status_code == 403


# ---------------------------------------------------------------- daily tasks

def test_daily_tasks_progress_and_claim_once(api, client):
    citizen = api.signup()
    tasks = {t["code"]: t for t in client.get("/tasks", headers=citizen).json["tasks"]}
    assert set(tasks) == {"report", "confirm", "cleanup"}
    assert not any(t["complete"] for t in tasks.values())
    r = client.post("/tasks/report/claim", headers=citizen)
    assert r.status_code == 409 and r.json["error"] == "task_not_done"

    assert api.report(citizen, synthetic.with_litter(synthetic.place(69), 4)).status_code == 201
    tasks = {t["code"]: t for t in client.get("/tasks", headers=citizen).json["tasks"]}
    assert tasks["report"]["complete"] and not tasks["report"]["claimed"]

    pending_before = api.me(citizen)["pending"]
    r = client.post("/tasks/report/claim", headers=citizen)
    assert r.status_code == 201 and r.json["points_pending"] == tasks["report"]["bonus"]
    assert api.me(citizen)["pending"] == pending_before + tasks["report"]["bonus"]
    again = client.post("/tasks/report/claim", headers=citizen)
    assert again.status_code == 409 and again.json["error"] == "task_already_claimed"
    tasks = {t["code"]: t for t in client.get("/tasks", headers=citizen).json["tasks"]}
    assert tasks["report"]["claimed"]
    assert client.post("/tasks/fly/claim", headers=citizen).status_code == 404


def test_cleanup_task_counts_verified_cleanups_only(api, client):
    cleaner, _result = verified_cleanup(api, seed=70)
    tasks = {t["code"]: t for t in client.get("/tasks", headers=cleaner).json["tasks"]}
    assert tasks["cleanup"]["complete"]
    assert client.post("/tasks/cleanup/claim", headers=cleaner).status_code == 201

    _rep, report, _scene = dirty_spot(api, seed=71, at=FAR)
    other, challenge = claimed(api, report["id"])
    r = api.cleanup(other, report["id"], challenge["id"],
                    synthetic.cleanup_frames(synthetic.place(72), challenge["instruction"]), *FAR)
    assert r.json["verdict"] == "review"
    tasks = {t["code"]: t for t in client.get("/tasks", headers=other).json["tasks"]}
    assert not tasks["cleanup"]["complete"]


# ---------------------------------------------------------------- what the phone shows on errors

def test_errors_carry_a_kurdish_message_and_claim_says_how_long(api, client):
    r = client.get("/me", headers={"Authorization": "Bearer expired-or-garbage"})
    assert r.status_code == 401 and r.json["error"] == "unauthorized" and r.json["message"] != "unauthorized"
    citizen = api.signup()
    r = client.get("/admin/stats", headers=citizen)
    assert r.status_code == 403 and r.json["message"] != "forbidden"
    r = client.get("/reports/999999", headers=citizen)
    assert r.status_code == 404 and r.json["message"] != "not_found"

    _rep, report, _scene = dirty_spot(api, seed=73)
    challenge = api.claim(citizen, report["id"]).json
    assert challenge["expires_in"] == Config.CHALLENGE_MINUTES * 60

    health = client.get("/health").json
    assert health["detector"] and health["model"].endswith(".pt")
