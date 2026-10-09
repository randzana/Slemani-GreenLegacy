"""The municipality dashboard (templates/dashboard.html + static/dashboard/): it loads without the internet,
every endpoint its JavaScript calls exists, every button has a handler, every text key exists, and the
backend pieces it relies on (stats for the badges, the sticker download, error messages) answer."""
import re
from pathlib import Path

import psycopg

from conftest import TEST_DB

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static" / "dashboard"
PAGE = ROOT / "app" / "templates" / "dashboard.html"
SCRIPTS = ("app.js", "core.js", "views.js", "map.js", "strings.js")


def source(*names):
    return "".join((STATIC / n).read_text(encoding="utf-8") for n in names)


def sql(statement, params=()):
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else None


def test_the_page_and_its_files_load_without_the_internet(client):
    page = client.get("/dashboard")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    # nothing from another host: the demo laptop may have no internet (map tiles excepted, in map.js)
    assert not re.search(r'(src|href)="(https?:)?//', html)
    for name in SCRIPTS + ("dashboard.css",):
        r = client.get(f"/static/dashboard/{name}")
        assert r.status_code == 200, name
        assert ("css" if name.endswith(".css") else "javascript") in r.content_type, (name, r.content_type)
    # module imports point at files that exist
    for name in SCRIPTS:
        for target in re.findall(r"from '\./([\w.]+)'", source(name)):
            assert (STATIC / target).is_file(), (name, target)


def test_every_endpoint_the_dashboard_calls_exists(app):
    calls = set()
    for m in re.finditer(r"""(?:api|download)\(\s*[`'"](/[^`'"]*)""", source("app.js", "views.js", "map.js")):
        path = m.group(1).split("?")[0]
        path = re.sub(r"\$\{[^}]*\}", "X", path)
        path = re.sub(r"\$\{.*$", "", path)              # a query string built inside ${...}
        calls.add(path)
    routes = {re.sub(r"<[^>]+>", "X", rule.rule) for rule in app.url_map.iter_rules()}
    assert calls and calls <= routes, calls - routes
    assert {"/admin/stats", "/admin/places/X/review", "/admin/pins/X/toggle", "/admin/bins/X/sticker"} <= calls


def test_every_button_has_a_handler_and_every_text_exists():
    views = source("views.js")
    block = views[views.index("export const actions = {"):views.index("/** One listener for every")]
    handlers = set(re.findall(r"^  '?([\w-]+)'?: ", block, re.M))
    used = set(re.findall(r'data-action(?:-change)?="([\w-]+)"', PAGE.read_text(encoding="utf-8") + views + source("map.js")))
    assert used and used <= handlers, used - handlers

    strings = source("strings.js")
    for key in re.findall(r'data-t(?:-placeholder|-aria)?="([\w.]+)"', PAGE.read_text(encoding="utf-8")):
        assert re.search(rf"^\s+{re.escape(key.split('.')[0])}:", strings, re.M), key


def test_the_page_keeps_one_view_per_nav_item():
    html = PAGE.read_text(encoding="utf-8")
    tabs = re.findall(r'data-tab="(\w+)"', html)
    views = re.findall(r'data-view="(\w+)"', html)
    assert tabs == views and len(tabs) == 11
    for badge in ("review-count", "places-count", "bin-count", "voucher-count"):
        assert f'id="{badge}"' in html


def test_stats_carry_the_badge_counts(client, api):
    staff = api.staff()
    s = client.get("/admin/stats", headers=staff).json
    assert (s["bins_total"], s["bins_full"], s["pins_active"], s["vouchers_waiting"]) == (0, 0, 0, 0)
    bin_id = client.post("/admin/bins", headers=staff, json={"name": "تەنەکەی پارک", "lat": 35.56, "lon": 45.43}).json["bin"]["id"]
    client.post(f"/admin/bins/{bin_id}/status", headers=staff, json={"status": "full"})
    client.post("/admin/pins", headers=staff, json={"title": "نەمام", "description": "ناشتن", "category": "tree_planting",
                                                    "lat": 35.56, "lon": 45.43})
    citizen = sql("SELECT id FROM users WHERE role = 'staff'")[0][0]
    sql("""INSERT INTO point_ledger (user_id, amount, kind, status, detail)
           VALUES (%s, 40, 'redeem', 'released', 'cloth_bag:GL-TEST01')""", (citizen,))
    s = client.get("/admin/stats", headers=staff).json
    assert (s["bins_total"], s["bins_full"], s["pins_active"], s["vouchers_waiting"]) == (1, 1, 1, 1)


def test_the_sticker_needs_the_staff_token(client, api):
    """Why the dashboard fetches the sticker instead of linking it: a link sends no token."""
    staff = api.staff()
    bin_id = client.post("/admin/bins", headers=staff, json={"name": "تەنەکە", "lat": 35.56, "lon": 45.43}).json["bin"]["id"]
    assert client.get(f"/admin/bins/{bin_id}/sticker").status_code == 401
    r = client.get(f"/admin/bins/{bin_id}/sticker", headers=staff)
    assert r.status_code == 200 and r.content_type == "image/png" and r.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_admin_errors_say_what_is_wrong_in_kurdish(client, api):
    staff = api.staff()
    for method, path, body, code in (("post", "/admin/cleanups/999999/review", {"decision": "approve"}, "not_reviewable"),
                                      ("post", "/admin/pins/999999/toggle", {}, "not_found"),
                                      ("get", "/admin/bins/999999/sticker", None, "not_found"),
                                      ("post", "/admin/bins/1/status", {"status": "broken"}, "invalid_status")):
        r = getattr(client, method)(path, headers=staff, json=body)
        assert r.json["error"] == code and r.json["message"] and r.json["message"] != code, (path, r.json)
