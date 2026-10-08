-- Neighbourhood boundaries become MULTIPOLYGONs (OSM areas often have several parts) with a spatial
-- index, for a database created with an earlier schema.sql, without losing its data:
--     psql "$DATABASE_URL" -f migrations/002_neighbourhood_boundaries.sql
-- Safe to run again. Existing polygons are kept as one-part multipolygons.
-- (A fresh `python seed.py` already has all of this, and wipes everything.)
BEGIN;
ALTER TABLE neighbourhoods ALTER COLUMN boundary TYPE GEOGRAPHY(MULTIPOLYGON, 4326)
    USING ST_Multi(boundary::geometry)::geography;
CREATE INDEX IF NOT EXISTS neighbourhoods_boundary_idx ON neighbourhoods USING GIST (boundary);
COMMIT;
