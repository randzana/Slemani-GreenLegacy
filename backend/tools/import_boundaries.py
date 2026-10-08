"""Load neighbourhood boundaries from a GeoJSON FeatureCollection into the neighbourhoods table.

    python tools/import_boundaries.py slemani.geojson                    # name from name:ckb, name:ku, name
    python tools/import_boundaries.py slemani.geojson --name-prop name:ckb
    python tools/import_boundaries.py slemani.geojson --add-missing      # also add names not in the database
    python tools/import_boundaries.py slemani.geojson --dry-run          # print what would change, save nothing

Make the file on a laptop with internet: on overpass-turbo.eu, zoom to the city, run a query such as
    [out:json][timeout:60];
    (way["place"~"neighbourhood|quarter|suburb"]({{bbox}});
     relation["place"~"neighbourhood|quarter|suburb"]({{bbox}}););
    out geom;
and Export -> GeoJSON; or draw the areas on geojson.io and give each a "name" property. Check the
areas on the map before importing: many OSM neighbourhoods are only a point (skipped here), and those
have to be drawn by hand. A feature matches a neighbourhood only when its name is spelt exactly like
the one in the database (seed.py); unmatched names are listed so they can be fixed in the file.
Polygons and MultiPolygons are stored as MultiPolygons; features with the same name are joined.
Uses DATABASE_URL like seed.py. On a database made before this tool, run
migrations/002_neighbourhood_boundaries.sql first.
"""
import argparse
import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import Config  # noqa: E402

NAME_PROPS = ("name:ckb", "name:ku", "name")
AREA_TYPES = ("Polygon", "MultiPolygon")


def feature_name(feature, name_props):
    """The first non-empty name property. Older overpass-turbo exports keep OSM tags under 'tags'."""
    props = feature.get("properties") or {}
    tags = props.get("tags") if isinstance(props.get("tags"), dict) else {}
    for key in name_props:
        value = props.get(key) or tags.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _positions(coords):
    if coords and isinstance(coords[0], (int, float)):
        yield coords
    else:
        for part in coords or []:
            yield from _positions(part)


def in_degrees(geometry):
    """GeoJSON must be lon/lat degrees (RFC 7946); a projected export (metres) would land nowhere."""
    return all(abs(p[0]) <= 180 and abs(p[1]) <= 90 for p in _positions(geometry.get("coordinates")))


def read_areas(path, name_props=NAME_PROPS):
    """Group the polygon features by name. Returns ({name: [geometry, ...]}, [skip messages])."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("type") == "Feature":
        data = {"features": [data]}
    if not isinstance(data.get("features"), list):
        raise SystemExit(f"{path}: not a GeoJSON FeatureCollection")
    areas, skipped = {}, []
    for i, feature in enumerate(data["features"], 1):
        name = feature_name(feature, name_props)
        label = f"feature {i}" + (f" ({name})" if name else "")
        geometry = feature.get("geometry") or {}
        kind = geometry.get("type")
        if kind not in AREA_TYPES:
            skipped.append(f"{label}: {kind or 'no geometry'}, not an area - skipped")
        elif name is None:
            skipped.append(f"{label}: no {' / '.join(name_props)} property - skipped")
        elif not in_degrees(geometry):
            skipped.append(f"{label}: coordinates are not lon/lat degrees (export as EPSG:4326) - skipped")
        else:
            areas.setdefault(name, []).append(geometry)
    return areas, skipped


# ST_MakeValid repairs hand-drawn self-crossing shapes (ST_Union and ST_Covers fail on them) and
# CollectionExtract(3) keeps only its polygons; the union then joins the parts that share a name.
AREA_SQL = """SELECT g, ST_IsEmpty(g::geometry) AS empty FROM (
    SELECT ST_Multi(ST_Union(ARRAY(
        SELECT ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(part), 4326)), 3)
        FROM unnest(%s::text[]) AS part)))::geography AS g) area"""


def import_boundaries(path, database_url=None, name_props=NAME_PROPS, add_missing=False, dry_run=False,
                      log=print):
    """Store each named area as the boundary of the neighbourhood with that exact name.
    Returns a summary dict; nothing is saved when dry_run is set."""
    areas, skipped = read_areas(path, name_props)
    summary = {"updated": [], "added": [], "unmatched": [], "skipped": skipped, "without_boundary": []}
    with psycopg.connect(database_url or Config.DATABASE_URL) as conn:
        known = {name for (name,) in conn.execute("SELECT name FROM neighbourhoods")}
        for name, geometries in areas.items():
            if name not in known and not add_missing:
                summary["unmatched"].append(name)
                continue
            area, empty = conn.execute(AREA_SQL, ([json.dumps(g) for g in geometries],)).fetchone()
            if empty:
                skipped.append(f"{name}: the shape has no area - skipped")
            elif name in known:
                conn.execute("UPDATE neighbourhoods SET boundary = %s::geography WHERE name = %s", (area, name))
                summary["updated"].append(name)
            else:
                conn.execute("INSERT INTO neighbourhoods (name, boundary) VALUES (%s, %s::geography)", (name, area))
                summary["added"].append(name)
            if len(geometries) > 1 and not empty:
                log(f"  {name}: joined {len(geometries)} features into one boundary")
        summary["without_boundary"] = [name for (name,) in conn.execute(
            "SELECT name FROM neighbourhoods WHERE boundary IS NULL ORDER BY name")]
        if dry_run:
            conn.rollback()

    for message in skipped:
        log("  " + message)
    log(f"updated {len(summary['updated'])}: {', '.join(summary['updated']) or '-'}")
    log(f"added {len(summary['added'])}: {', '.join(summary['added']) or '-'}")
    if summary["unmatched"]:
        log(f"not in the database {len(summary['unmatched'])} (fix the spelling, or use --add-missing): "
            + ", ".join(summary["unmatched"]))
    log(f"skipped features {len(skipped)}")
    log(f"neighbourhoods still without a boundary {len(summary['without_boundary'])}: "
        + (", ".join(summary["without_boundary"]) or "-"))
    if dry_run:
        log("dry run: nothing saved")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("geojson", help="GeoJSON FeatureCollection (lon/lat, EPSG:4326)")
    parser.add_argument("--name-prop", action="append",
                        help=f"property holding the name; repeat to try several (default: {', '.join(NAME_PROPS)})")
    parser.add_argument("--add-missing", action="store_true", help="insert neighbourhoods not in the database")
    parser.add_argument("--dry-run", action="store_true", help="report only, save nothing")
    args = parser.parse_args()
    import_boundaries(args.geojson, name_props=tuple(args.name_prop or NAME_PROPS),
                      add_missing=args.add_missing, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
