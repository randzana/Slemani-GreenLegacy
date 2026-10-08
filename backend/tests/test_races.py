"""Requests that arrive at the same moment, and other ways to be paid twice. Each thread has its
own test client, so every request gets its own database connection, as on the threaded server."""
import io
import threading

import psycopg

from conftest import SLEMANI, STAFF, TEST_DB, Api
from seed import seed
from test_flow import claimed, dirty_spot
from tools import synthetic


def at_once(n, fn):
    """Run fn(i) in n threads released together; return the results in order."""
    barrier, results = threading.Barrier(n), [None] * n

    def run(i):
        barrier.wait()
        results[i] = fn(i)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def post_cleanup(app, headers, report_id, challenge_id, frames):
    data = {"lat": str(SLEMANI[0]), "lon": str(SLEMANI[1]), "challenge_id": str(challenge_id),
            "frames": [(io.BytesIO(synthetic.encode(f)), f"f{i}.jpg") for i, f in enumerate(frames)]}
    r = app.test_client().post(f"/reports/{report_id}/cleanup", data=data, headers=headers,
                               content_type="multipart/form-data")
    return r.status_code, r.json


def test_the_same_cleanup_sent_three_times_at_once_is_paid_once(api, app):
    _rep, report, scene = dirty_spot(api, seed=90)
    cleaner, challenge = claimed(api, report["id"])
    frames = synthetic.cleanup_frames(scene, challenge["instruction"])
    results = at_once(3, lambda i: post_cleanup(app, cleaner, report["id"], challenge["id"], frames))
    verdicts = [body.get("verdict") for _status, body in results]
    assert verdicts.count("verified") == 1, results
    with psycopg.connect(TEST_DB) as conn:
        paid = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM point_ledger WHERE kind = 'cleanup'").fetchone()[0]
        rows = conn.execute("SELECT count(*) FROM cleanups WHERE verdict = 'verified'").fetchone()[0]
    from app.config import Config
    assert rows == 1 and paid == Config.CLEANUP_POINTS[report["dirtiness"]]
    assert api.me(cleaner)["trust_level"] == 1


def test_parallel_claims_give_one_live_challenge(api, app):
    _rep, report, _scene = dirty_spot(api, seed=91)
    cleaner = api.signup()
    results = at_once(5, lambda i: app.test_client().post(f"/reports/{report['id']}/claim", headers=cleaner))
    ids = {r.json["id"] for r in results}
    assert len(ids) == 1 and sorted(r.status_code for r in results) == [200, 200, 200, 200, 201]

    _rep2, report2, _scene2 = dirty_spot(api, seed=92, at=(SLEMANI[0] + 0.02, SLEMANI[1]))
    people = [api.signup() for _ in range(4)]
    results = at_once(4, lambda i: app.test_client().post(f"/reports/{report2['id']}/claim", headers=people[i]))
    assert sorted(r.status_code for r in results) == [201, 409, 409, 409]


def test_a_late_upload_does_not_hand_back_someone_elses_claim(api, client):
    _rep, report, scene = dirty_spot(api, seed=93)
    late, old = claimed(api, report["id"])
    with psycopg.connect(TEST_DB) as conn:
        conn.execute("UPDATE challenges SET expires_at = now() - interval '1 second' WHERE id = %s", (old["id"],))
    client.get("/reports", headers=late)                      # housekeeping reopens the abandoned spot
    other, live = claimed(api, report["id"])
    r = api.cleanup(late, report["id"], old["id"], synthetic.cleanup_frames(scene, old["instruction"]))
    assert r.json["reason_code"] == "challenge_expired"
    assert client.get(f"/reports/{report['id']}", headers=other).json["status"] == "in_progress"
    r = api.cleanup(other, report["id"], live["id"], synthetic.cleanup_frames(scene, live["instruction"]))
    assert r.json["verdict"] == "verified"


def test_using_up_a_challenge_on_purpose_does_not_draw_a_new_instruction(api):
    _rep, report, _scene = dirty_spot(api, seed=94)
    cleaner, first = claimed(api, report["id"])
    r = api.cleanup(cleaner, report["id"], first["id"], [])
    assert r.json["reason_code"] == "too_few_frames"
    for _ in range(4):
        again = api.claim(cleaner, report["id"]).json
        assert again["id"] != first["id"] and again["instruction"] == first["instruction"]
        api.cleanup(cleaner, report["id"], again["id"], [])


def test_a_token_from_before_a_reseed_is_refused(tmp_path):
    import datetime as dt

    import jwt

    from app import create_app
    from app.ai.detector import ColorBlobDetector
    seed(TEST_DB, *STAFF)
    app = create_app({"DATABASE_URL": TEST_DB, "UPLOAD_DIR": str(tmp_path), "TESTING": True},
                     detector=ColorBlobDetector())
    Api(app.test_client()).signup("داریا")                    # users.id 2, at the evening rehearsal
    now = dt.datetime.now(dt.timezone.utc)
    rehearsal_token = jwt.encode({"sub": "2", "role": "citizen", "iat": now - dt.timedelta(hours=1),
                                  "exp": now + dt.timedelta(days=1)}, app.config["SECRET_KEY"], algorithm="HS256")
    seed(TEST_DB, *STAFF)                                     # the hour-before re-seed, same SECRET_KEY
    dadyar = Api(app.test_client())
    dadyar._phone += 50
    dadyar_headers = dadyar.signup("دادیار")                  # gets users.id 2 now
    stale = {"Authorization": f"Bearer {rehearsal_token}"}
    assert app.test_client().get("/me", headers=stale).status_code == 401
    assert app.test_client().get("/me", headers=dadyar_headers).json["name"] == "دادیار"


def test_a_voucher_is_handed_over_once(api, client, app):
    from test_extras import end_holds, verified_cleanup
    cleaner, _result = verified_cleanup(api, seed=95)
    end_holds()
    app.config["REWARDS"] = {**app.config["REWARDS"], "cloth_bag": 1}
    voucher = client.post("/rewards/cloth_bag/redeem", headers=cleaner).json["voucher"]
    staff = api.staff()
    row = next(r for r in client.get("/admin/redemptions", headers=staff).json if r["voucher"] == voucher)
    assert row["honoured_at"] is None
    assert client.post(f"/admin/redemptions/{row['id']}/honour", headers=staff).status_code == 200
    again = client.post(f"/admin/redemptions/{row['id']}/honour", headers=staff)
    assert again.status_code == 409 and again.json["message"]
    assert client.post(f"/admin/redemptions/{row['id']}/honour", headers=cleaner).status_code == 403
    mine = client.get("/rewards", headers=cleaner).json["vouchers"]
    assert [v["honoured"] for v in mine if v["voucher"] == voucher] == [True]
