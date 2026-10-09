"""Staff and places: the review queue, decisions with reasons, and the monthly money."""
import datetime as dt

import psycopg
import pytest

from conftest import TEST_DB
from test_accounts import HOME, SHOP

THIS_MONTH = dt.date.today().strftime("%Y-%m")


def sql(statement, params=()):
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else None


@pytest.fixture()
def owner(api):
    """A person with a household and a business, both waiting for staff."""
    return api.signup("ئاسۆ", household=HOME, business=SHOP)


def queue(client, staff, status="pending"):
    return {p["kind"]: p for p in client.get(f"/admin/places?status={status}", headers=staff).json}


def decide(client, staff, place, decision, reason=None, **extra):
    return client.post(f"/admin/places/{place['id']}/review", headers=staff,
                       json={"decision": decision, "reason": reason, "updated_at": place["updated_at"], **extra})


def test_only_staff(client, api, owner):
    for method, path in (("get", "/admin/places"), ("post", "/admin/places/1/review"), ("get", "/admin/payments"),
                         ("post", "/admin/places/1/payments"), ("post", "/admin/payments")):
        assert getattr(client, method)(path, headers=owner, json={}).status_code == 403, path
        assert getattr(client, method)(path, json={}).status_code == 401, path


def test_the_queue_shows_what_staff_need_to_check(client, api, owner):
    places = queue(client, api.staff())
    home, shop = places["household"], places["business"]
    assert home["owner_name"] == shop["owner_name"] == "ئاسۆ" and home["owner_phone"].startswith("+9647")
    assert (home["lat"], home["lon"], home["residents_count"]) == (HOME["lat"], HOME["lon"], 4)
    assert (shop["category_name"], shop["license_number"]) == ("کافێ", "SUL-1234")
    assert queue(client, api.staff(), "verified") == {}


def test_verify_and_reject_with_a_reason_the_owner_sees(client, api, owner):
    staff = api.staff()
    home, shop = queue(client, staff)["household"], queue(client, staff)["business"]
    ok = decide(client, staff, home, "verify")
    assert ok.status_code == 200 and ok.json["verification_status"] == "verified" and ok.json["verified_at"]

    refused = decide(client, staff, shop, "reject", reason="  ")
    assert refused.status_code == 400 and refused.json["error"] == "reason_required"
    assert decide(client, staff, shop, "maybe").json["error"] == "bad_decision"
    r = decide(client, staff, shop, "reject", reason="ژمارەی مۆڵەتەکە هەڵەیە")
    assert r.json["verification_status"] == "rejected"
    mine = {p["kind"]: p for p in client.get("/me", headers=owner).json["places"]}
    assert mine["business"]["rejection_reason"] == "ژمارەی مۆڵەتەکە هەڵەیە"
    assert mine["household"]["verification_status"] == "verified"

    # a second look: verifying it now clears the reason; every decision is kept, with who made it
    again = decide(client, staff, r.json, "verify")
    assert again.json["verification_status"] == "verified" and again.json["rejection_reason"] is None
    staff_id = sql("SELECT id FROM users WHERE role = 'staff'")[0][0]
    assert sql("""SELECT status, reason, changed_by FROM place_reviews WHERE place_id = %s ORDER BY id""",
               (shop["id"],)) == [("pending", None, shop["owner_id"]),
                                  ("rejected", "ژمارەی مۆڵەتەکە هەڵەیە", staff_id), ("verified", None, staff_id)]
    assert sql("SELECT verified_by FROM places WHERE id = %s", (shop["id"],)) == [(staff_id,)]
    assert decide(client, staff, {"id": 999999, "updated_at": None}, "verify").status_code == 404


def test_a_place_changed_after_staff_looked_is_not_approved_unseen(client, api, owner):
    staff = api.staff()
    seen = queue(client, staff)["household"]
    client.post("/me/places", json={"kind": "household", **HOME, "residents_count": 12}, headers=owner)
    r = decide(client, staff, seen, "verify")
    assert r.status_code == 409 and r.json["error"] == "place_changed"
    fresh = queue(client, staff)["household"]
    assert fresh["residents_count"] == 12 and decide(client, staff, fresh, "verify").status_code == 200


def test_crediting_one_place_once_a_month(client, api, owner):
    staff = api.staff()
    home, shop = queue(client, staff)["household"], queue(client, staff)["business"]

    def credit(place, **body):
        return client.post(f"/admin/places/{place['id']}/payments", headers=staff,
                           json={"month": THIS_MONTH, "amount_iqd": 10000, **body})

    assert credit(home).json["error"] == "place_not_verified"          # not checked yet: no money
    decide(client, staff, home, "verify")
    for bad in ({"month": "2026-13"}, {"month": "next month"}, {"month": "2999-01"}, {"month": "2023-12"}):
        assert credit(home, **bad).json["error"] == "invalid_month", bad
    for bad in (0, -5, "10000", 10.5, True, 1_000_001):
        assert credit(home, amount_iqd=bad).json["error"] == "invalid_amount", bad
    r = credit(home, note="مانگی یەکەم")
    assert r.status_code == 201 and r.json["amount_iqd"] == 10000
    again = credit(home, amount_iqd=99999)
    assert again.status_code == 409 and again.json["error"] == "already_paid"
    assert credit({"id": 999999}).status_code == 404
    assert sql("SELECT amount_iqd, note FROM place_payments") == [(10000, "مانگی یەکەم")]
    assert client.get("/me", headers=owner).json["money"]["total_iqd"] == 10000


def test_crediting_every_verified_place_for_a_month(client, api, owner):
    staff = api.staff()
    other = api.signup("دلێر", household={**HOME, "name": "ماڵی دلێر"})
    for place in client.get("/admin/places", headers=staff).json:
        if place["owner_name"] == "ئاسۆ":                        # دلێر's home stays pending
            decide(client, staff, place, "verify")
    body = {"month": THIS_MONTH, "household_iqd": 10000, "business_iqd": 25000}
    assert client.post("/admin/payments", headers=staff, json={**body, "business_iqd": 0}).json["error"] == "invalid_amount"
    r = client.post("/admin/payments", headers=staff, json=body)
    assert r.json == {"month": THIS_MONTH, "credited": 2}          # دلێر's home is still pending
    assert client.post("/admin/payments", headers=staff, json=body).json["credited"] == 0

    month = client.get(f"/admin/payments?month={THIS_MONTH}", headers=staff).json
    assert month["defaults"] == {"household": 10000, "business": 25000} and month["total_iqd"] == 35000
    assert sorted((p["kind"], p["paid_iqd"]) for p in month["places"]) == [("business", 25000), ("household", 10000)]
    assert client.get("/me", headers=owner).json["money"]["total_iqd"] == 35000
    assert client.get("/me", headers=other).json["money"]["total_iqd"] == 0
    assert client.get("/admin/payments?month=2999-01", headers=staff).json["error"] == "invalid_month"
    assert client.get("/admin/payments", headers=staff).json["month"] == THIS_MONTH


def test_stats_and_homes_per_neighbourhood(client, api, owner):
    staff = api.staff()
    stats = client.get("/admin/stats", headers=staff).json
    assert (stats["households"], stats["businesses"], stats["pending_places"]) == (0, 0, 2)
    decide(client, staff, queue(client, staff)["household"], "verify")
    stats = client.get("/admin/stats", headers=staff).json
    assert (stats["households"], stats["pending_places"]) == (1, 1)
    # no boundaries loaded and none on the form: the home counts in its family's neighbourhood (1)
    hoods = {h["id"]: h for h in client.get("/admin/neighbourhoods", headers=staff).json}
    assert hoods[1]["households"] == 1 and sum(h["households"] for h in hoods.values()) == 1
    text = client.get("/admin/neighbourhoods", headers=staff).get_data(as_text=True)
    assert str(HOME["lat"]) not in text and str(HOME["lon"]) not in text      # counted, never located


def test_the_dashboard_has_the_new_tabs(client):
    page = client.get("/dashboard").get_data(as_text=True)
    assert 'data-tab="places"' in page and 'data-tab="money"' in page and 'id="places-count"' in page
