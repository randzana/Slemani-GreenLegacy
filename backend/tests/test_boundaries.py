"""Neighbourhood boundaries: the GeoJSON import tool, /neighbourhoods?geo=1, the staff league
(/admin/neighbourhoods) and migration 002. The squares are synthetic test shapes, not real boundaries."""
import json
from pathlib import Path

import psycopg
import pytest

from conftest import SLEMANI, TEST_DB
from seed import NEIGHBOURHOODS
from test_flow import FAR, claimed, dirty_spot
from tools import synthetic
from tools.import_boundaries import import_boundaries

INSIDE, OTHER, NO_AREA = NEIGHBOURHOODS[:3]           # ids 1, 2, 3 after seed()
OTHER_CENTRE = (SLEMANI[0], SLEMANI[1] + 0.02)        # about 1.8 km east, no overlap
NEW_NAME = "گەڕەکی تاقیکردنەوە"
MIGRATION = Path(__file__).resolve().parent.parent / "migrations" / "002_neighbourhood_boundaries.sql"


def square(lat, lon, half=0.005):
    """One closed lon/lat ring, about 1.1 km across."""
    return [[[lon - half, lat - half], [lon + half, lat - half], [lon + half, lat + half],
             [lon - half, lat + half], [lon - half, lat - half]]]


def feature(props, kind, coords):
    return {"type": "Feature", "properties": props, "geometry": {"type": kind, "coordinates": coords}}


def write_geojson(path, features):
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
                    encoding="utf-8")
    return path


def quiet(_line):
    pass


@pytest.fixture()
def geojson(tmp_path):
    return write_geojson(tmp_path / "areas.geojson", [
        feature({"name:ckb": INSIDE, "name": "Sarchnar"}, "Polygon", square(*SLEMANI)),
        feature({"name": OTHER}, "MultiPolygon", [square(*OTHER_CENTRE)]),
        feature({"name": NEW_NAME}, "Polygon", square(SLEMANI[0] - 0.03, SLEMANI[1])),
        feature({"name": INSIDE}, "Point", [SLEMANI[1], SLEMANI[0]]),     # a label node, as OSM exports have
    ])


def with_boundary():
    with psycopg.connect(TEST_DB) as conn:
        return conn.execute("SELECT count(*) FROM neighbourhoods WHERE boundary IS NOT NULL").fetchone()[0]


# ---------------------------------------------------------------- import tool

def test_import_matches_names_and_skips_points(app, geojson):
    lines = []
    summary = import_boundaries(geojson, TEST_DB, log=lines.append)
    assert summary["updated"] == [INSIDE, OTHER]                  # name:ckb wins over name
    assert summary["added"] == [] and summary["unmatched"] == [NEW_NAME]
    assert len(summary["skipped"]) == 1 and "Point" in summary["skipped"][0]
    assert sorted(summary["without_boundary"]) == sorted(NEIGHBOURHOODS[2:])
    assert any(NEW_NAME in line and "--add-missing" in line for line in lines)
    assert with_boundary() == 2


def test_import_dry_run_and_add_missing(app, geojson):
    import_boundaries(geojson, TEST_DB, add_missing=True, dry_run=True, log=quiet)
    assert with_boundary() == 0
    summary = import_boundaries(geojson, TEST_DB, add_missing=True, log=quiet)
    assert summary["added"] == [NEW_NAME] and summary["unmatched"] == []
    assert with_boundary() == 3


def test_import_repairs_crossing_shapes_and_joins_parts(app, tmp_path):
    lon, lat = SLEMANI[1], SLEMANI[0]
    bowtie = [[[lon, lat], [lon + 0.01, lat + 0.01], [lon + 0.01, lat], [lon, lat + 0.01], [lon, lat]]]
    path = write_geojson(tmp_path / "messy.geojson", [
        feature({"name": INSIDE}, "Polygon", bowtie),                        # hand-drawn, crosses itself
        feature({"name": OTHER}, "Polygon", square(*SLEMANI)),
        feature({"name": OTHER}, "Polygon", square(*OTHER_CENTRE)),          # second part, same name
    ])
    summary = import_boundaries(path, TEST_DB, log=quiet)
    assert summary["updated"] == [INSIDE, OTHER]
    with psycopg.connect(TEST_DB) as conn:
        rows = dict(conn.execute(
            """SELECT name, ARRAY[ST_IsValid(boundary::geometry)::int, ST_NumGeometries(boundary::geometry)]
               FROM neighbourhoods WHERE boundary IS NOT NULL""").fetchall())
    assert rows == {INSIDE: [1, 2], OTHER: [1, 2]}


# ---------------------------------------------------------------- endpoints

def test_neighbourhoods_list_and_geo(client, geojson):
    import_boundaries(geojson, TEST_DB, log=quiet)
    plain = client.get("/neighbourhoods").json
    assert len(plain) == len(NEIGHBOURHOODS) and all(set(n) == {"id", "name"} for n in plain)
    geo = {n["name"]: n["boundary"] for n in client.get("/neighbourhoods?geo=1").json}
    assert geo[INSIDE]["type"] == geo[OTHER]["type"] == "MultiPolygon"
    assert geo[NO_AREA] is None
    ring = geo[INSIDE]["coordinates"][0][0]
    assert min(p[0] for p in ring) == pytest.approx(SLEMANI[1] - 0.005)


def test_league_counts_spots_inside_the_boundary(api, geojson):
    import_boundaries(geojson, TEST_DB, log=quiet)
    # a cleaned spot and an open spot inside the first square, and one open spot outside both
    _r, report, scene = dirty_spot(api, seed=71, at=SLEMANI)
    cleaner, challenge = claimed(api, report["id"])
    r = api.cleanup(cleaner, report["id"], challenge["id"],
                    synthetic.cleanup_frames(scene, challenge["instruction"]), *SLEMANI)
    assert r.json["verdict"] == "verified", r.json
    _r, open_report, _s = dirty_spot(api, seed=72, at=(SLEMANI[0] + 0.003, SLEMANI[1]))
    dirty_spot(api, seed=73, at=FAR)
    with psycopg.connect(TEST_DB) as conn:                        # pretend the 24 h holds are over
        conn.execute("UPDATE point_ledger SET release_at = now() - interval '1 minute' WHERE release_at IS NOT NULL")

    league = api.client.get("/admin/neighbourhoods", headers=api.staff()).json
    rows = {row["name"]: row for row in league}
    inside, other, no_area = rows[INSIDE], rows[OTHER], rows[NO_AREA]
    assert (inside["open"], inside["cleaned"]) == (1, 1)
    assert inside["avg_dirtiness"] == open_report["dirtiness"]
    assert (other["open"], other["cleaned"], other["avg_dirtiness"]) == (0, 0, None)
    assert other["boundary"]["type"] == "MultiPolygon"
    assert no_area["boundary"] is None and (no_area["open"], no_area["cleaned"]) == (0, 0)
    assert inside["citizens"] == 4 and other["citizens"] == 0      # three reporters and the cleaner

    board = api.client.get("/leaderboard", headers=cleaner).json["neighbourhoods"]
    assert {h["name"]: h["points"] for h in board}[INSIDE] == inside["points"] > 0
    assert league[0]["name"] == INSIDE                             # most points first


def test_league_is_staff_only(api):
    citizen = api.signup()
    assert api.client.get("/admin/neighbourhoods", headers=citizen).status_code == 403
    assert api.client.get("/admin/neighbourhoods").status_code == 401


# ---------------------------------------------------------------- migration

def test_migration_turns_polygons_into_multipolygons(app):
    lon, lat = SLEMANI[1], SLEMANI[0]
    wkt = f"SRID=4326;POLYGON(({lon} {lat},{lon + 0.01} {lat},{lon + 0.01} {lat + 0.01},{lon} {lat + 0.01},{lon} {lat}))"
    sql = MIGRATION.read_text(encoding="utf-8")
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        # the column as the earlier schema.sql made it, with one polygon in it
        conn.execute("DROP INDEX neighbourhoods_boundary_idx")
        conn.execute("ALTER TABLE neighbourhoods ALTER COLUMN boundary TYPE GEOGRAPHY(POLYGON, 4326) USING NULL")
        conn.execute("UPDATE neighbourhoods SET boundary = ST_GeogFromText(%s) WHERE id = 1", (wkt,))
        area_before = conn.execute("SELECT ST_Area(boundary) FROM neighbourhoods WHERE id = 1").fetchone()[0]
        conn.execute(sql)
        conn.execute(sql)                                          # safe to run twice
        kind = conn.execute("""SELECT type FROM geography_columns
                               WHERE f_table_name = 'neighbourhoods' AND f_geography_column = 'boundary'""").fetchone()[0]
        parts, area = conn.execute("""SELECT ST_NumGeometries(boundary::geometry), ST_Area(boundary)
                                      FROM neighbourhoods WHERE id = 1""").fetchone()
        index = conn.execute("SELECT 1 FROM pg_indexes WHERE indexname = 'neighbourhoods_boundary_idx'").fetchone()
    assert kind == "MultiPolygon" and parts == 1 and area == pytest.approx(area_before)
    assert index is not None
