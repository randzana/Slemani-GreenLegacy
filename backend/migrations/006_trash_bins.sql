-- Trash bins with QR stickers and the points for using them, for a database created with an earlier
-- schema.sql, without losing its data:
--     psql "$DATABASE_URL" -f migrations/006_trash_bins.sql
-- Safe to run again. (A fresh `python seed.py` already has all of this, and wipes everything.)
BEGIN;
CREATE TABLE IF NOT EXISTS trash_bins (
    id               SERIAL PRIMARY KEY,
    code             TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL,
    bin_type         TEXT NOT NULL DEFAULT 'general' CHECK (bin_type IN ('general', 'recycle', 'organic', 'glass_metal')),
    capacity_liters  INTEGER NOT NULL DEFAULT 240,
    status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'full', 'maintenance')),
    location         GEOGRAPHY(POINT, 4326) NOT NULL,
    neighbourhood_id INTEGER REFERENCES neighbourhoods(id),
    qr_code_data     TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS trash_bins_location_idx ON trash_bins USING GIST (location);
CREATE INDEX IF NOT EXISTS trash_bins_code_idx ON trash_bins (code);

CREATE TABLE IF NOT EXISTS bin_disposals (
    id               SERIAL PRIMARY KEY,
    bin_id           INTEGER NOT NULL REFERENCES trash_bins(id) ON DELETE CASCADE,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    points_awarded   INTEGER NOT NULL DEFAULT 15,
    location         GEOGRAPHY(POINT, 4326),
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bin_disposals_bin_idx ON bin_disposals (bin_id);
CREATE INDEX IF NOT EXISTS bin_disposals_user_idx ON bin_disposals (user_id);

-- the ledger row for a disposal; 001 rewrote the kind check without 'bin_disposal'
ALTER TABLE point_ledger ADD COLUMN IF NOT EXISTS bin_id INTEGER;
ALTER TABLE point_ledger DROP CONSTRAINT IF EXISTS point_ledger_kind_check;
ALTER TABLE point_ledger ADD CONSTRAINT point_ledger_kind_check
    CHECK (kind IN ('report', 'confirmation', 'cleanup', 'task', 'redeem', 'bin_disposal'));
COMMIT;
