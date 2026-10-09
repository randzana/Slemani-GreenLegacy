"""Points shop, daily tasks, ranks, trust score and the Kurdish photo description."""
import time

import numpy as np
import psycopg
import pytest

from app import create_app
from app.ai.describe import template_description
from app.ai.detector import ColorBlobDetector
from app.otp import FakeOtpSender
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
                     detector=ColorBlobDetector(), describer=describer, otp_sender=FakeOtpSender())
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


# ---------------------------------------------------------------- the same place, honestly, twice

def test_same_angle_confirmation_is_accepted_without_points(api):
    reporter, report, scene = dirty_spot(api, seed=74)
    confirmer = api.signup()
    same_photo_again = synthetic.with_litter(scene, 6, 74)          # what a second account resending it sees
    r = api.report(confirmer, same_photo_again, *NEAR)
    assert r.status_code == 200 and r.json["kind"] == "confirmation"
    assert r.json["points_pending"] == 0
    assert api.me(reporter)["released"] == 0                        # nobody's held points were freed by it
    assert api.me(reporter)["trust_level"] == 0


def test_claiming_again_keeps_the_same_instruction(api):
    _rep, report, _scene = dirty_spot(api, seed=75)
    cleaner = api.signup()
    first = api.claim(cleaner, report["id"])
    again = api.claim(cleaner, report["id"])
    assert first.status_code == 201 and again.status_code == 200
    assert again.json["id"] == first.json["id"] and again.json["instruction"] == first.json["instruction"]
    assert 0 < again.json["expires_in"] <= first.json["expires_in"]


def test_a_corner_that_gets_dirty_again_goes_to_review_not_fraud(api):
    _rep, report, scene = dirty_spot(api, seed=76)
    cleaner, challenge = claimed(api, report["id"])
    frames = synthetic.cleanup_frames(scene, challenge["instruction"])
    assert api.cleanup(cleaner, report["id"], challenge["id"], frames).json["verdict"] == "verified"

    # a week later the same corner is dirty again and someone reports it
    again = api.signup()
    r = api.report(again, synthetic.with_litter(scene, 5, 300))
    assert r.status_code == 201, r.json
    second = r.json["report"]
    challenge2 = api.claim(cleaner, second["id"]).json
    r = api.cleanup(cleaner, second["id"], challenge2["id"],
                    synthetic.cleanup_frames(scene, challenge2["instruction"]))
    assert r.json["verdict"] == "review" and r.json["reason_code"] == "similar_to_earlier"
    assert api.me(cleaner)["trust_level"] == 1                      # the honest cleaner is not punished


def test_black_frames_do_not_make_an_honest_cleanup_look_reused(api):
    black = np.zeros((synthetic.H, synthetic.W, 3), dtype=np.uint8)
    for seed, at in ((77, synthetic_spot(77)), (78, FAR)):
        _rep, report, scene = dirty_spot(api, seed=seed, at=at)
        cleaner, challenge = claimed(api, report["id"])
        frames = synthetic.cleanup_frames(scene, challenge["instruction"])
        frames = frames[:-1] + [black] if challenge["instruction"] == "qr_first" else [black] + frames[1:]
        r = api.cleanup(cleaner, report["id"], challenge["id"], frames, *at)
        assert r.json["verdict"] == "verified", r.json


def test_admin_pin_creation_and_citizen_notifications(api):
    staff_auth = api.staff()
    citizen_auth = api.signup()

    # 1. Staff creates a tree planting pin with broadcast notification
    pin_payload = {
        "title": "هەڵمەتی چاندنی ٥٠ نەمام لە پارکی ئازادی",
        "description": "پێویستمان بە خۆبەخشانە بۆ چاندنی نەمامی چنار",
        "category": "tree_planting",
        "lat": 35.5613,
        "lon": 45.4373,
        "target_count": 50,
        "reward_points": 25,
        "notify_citizens": True,
    }
    r = api.client.post("/admin/pins", json=pin_payload, headers=staff_auth)
    assert r.status_code == 201, r.json
    pin = r.json["pin"]
    assert pin["title"] == pin_payload["title"]
    assert pin["category"] == "tree_planting"
    assert pin["reward_points"] == 25

    # 2. Staff creates a dirty spot pin without notification
    waste_payload = {
        "title": "شوێنی فڕێدانی پاشماوە لە چوارباخ",
        "description": "کۆمەڵێک زبڵ و خاشاک لەسەر شەقامەکە کەوتووە",
        "category": "cleanup_target",
        "lat": 35.5620,
        "lon": 45.4380,
        "notify_citizens": False,
    }
    r2 = api.client.post("/admin/pins", json=waste_payload, headers=staff_auth)
    assert r2.status_code == 201, r2.json

    # 3. Citizen fetches active pins
    r_pins = api.client.get("/pins", headers=citizen_auth)
    assert r_pins.status_code == 200
    pins_list = r_pins.json
    assert len(pins_list) >= 2
    categories = [p["category"] for p in pins_list]
    assert "tree_planting" in categories
    assert "cleanup_target" in categories

    # 4. Citizen fetches notifications (should have the broadcast notification)
    r_notifs = api.client.get("/notifications", headers=citizen_auth)
    assert r_notifs.status_code == 200
    notifs = r_notifs.json
    assert len(notifs) >= 1
    found_notif = next((n for n in notifs if n["pin_id"] == pin["id"]), None)
    assert found_notif is not None
    assert found_notif["category"] == "tree_planting"
    assert found_notif["is_read"] is False

    # 5. Citizen marks notification as read
    r_read = api.client.post(f"/notifications/{found_notif['id']}/read", headers=citizen_auth)
    assert r_read.status_code == 200
    assert r_read.json["ok"] is True

    # 6. Staff lists pins and deletes one
    r_admin_pins = api.client.get("/admin/pins", headers=staff_auth)
    assert r_admin_pins.status_code == 200
    assert len(r_admin_pins.json) >= 2

    del_r = api.client.delete(f"/admin/pins/{pin['id']}", headers=staff_auth)
    assert del_r.status_code == 200


def test_tree_planting_volunteer_registration(api):
    staff_auth = api.staff()
    citizen1_auth = api.signup("خۆبەخش ئاکۆ")
    citizen2_auth = api.signup("خۆبەخش باخان")

    # 1. Staff creates tree planting pin
    pin_payload = {
        "title": "هەڵمەتی ناشتنی ١٠٠ نەمامی بەڕوو لە گوێژە",
        "description": "پێویستمان بە خۆبەخشانە لە ڕۆژی هەینی",
        "category": "tree_planting",
        "lat": 35.5650,
        "lon": 45.4400,
        "target_count": 100,
        "reward_points": 75,
        "notify_citizens": True,
    }
    r = api.client.post("/admin/pins", json=pin_payload, headers=staff_auth)
    assert r.status_code == 201
    pin_id = r.json["pin"]["id"]

    # 2. Citizen 1 registers
    r_reg1 = api.client.post(f"/pins/{pin_id}/register", json={"notes": "بە خاکەناز و کەرەستەوە ئامادە دەبم"}, headers=citizen1_auth)
    assert r_reg1.status_code == 200
    assert r_reg1.json["ok"] is True
    assert r_reg1.json["registered"] is True
    assert r_reg1.json["participant_count"] == 1

    # 3. Citizen 2 registers
    r_reg2 = api.client.post(f"/pins/{pin_id}/register", json={"notes": "لەگەڵ ٢ هاوڕێم دێین"}, headers=citizen2_auth)
    assert r_reg2.status_code == 200
    assert r_reg2.json["participant_count"] == 2

    # 4. Citizen 1 checks pin details
    r_pin_detail = api.client.get(f"/pins/{pin_id}", headers=citizen1_auth)
    assert r_pin_detail.status_code == 200
    assert r_pin_detail.json["participant_count"] == 2
    assert r_pin_detail.json["user_registered"] is True

    # 5. Staff inspects participants list
    r_parts = api.client.get(f"/admin/pins/{pin_id}/participants", headers=staff_auth)
    assert r_parts.status_code == 200
    assert r_parts.json["count"] == 2
    names = [p["user_name"] for p in r_parts.json["participants"]]
    assert "خۆبەخش ئاکۆ" in names
    assert "خۆبەخش باخان" in names

    # 6. Citizen 2 unregisters
    r_unreg = api.client.post(f"/pins/{pin_id}/unregister", headers=citizen2_auth)
    assert r_unreg.status_code == 200
    assert r_unreg.json["registered"] is False
    assert r_unreg.json["participant_count"] == 1

    # 7. Verify count is now 1
    r_parts_after = api.client.get(f"/admin/pins/{pin_id}/participants", headers=staff_auth)
    assert r_parts_after.status_code == 200
    assert r_parts_after.json["count"] == 1
    assert r_parts_after.json["participants"][0]["user_name"] == "خۆبەخش ئاکۆ"


