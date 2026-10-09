-- Migration 004: Custom pins and mobile broadcast notifications
BEGIN;

CREATE TABLE IF NOT EXISTS pins (
    id                  SERIAL PRIMARY KEY,
    creator_id          INTEGER REFERENCES users(id),
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    category            TEXT NOT NULL CHECK (category IN ('tree_planting', 'cleanup_target', 'watering_point')),
    location            GEOGRAPHY(POINT, 4326) NOT NULL,
    target_count        INTEGER NOT NULL DEFAULT 1,
    reward_points       INTEGER NOT NULL DEFAULT 50,
    status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
    neighbourhood_id    INTEGER REFERENCES neighbourhoods(id),
    send_notification   BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS pins_location_idx ON pins USING GIST (location);
CREATE INDEX IF NOT EXISTS pins_status_idx ON pins (status);

CREATE TABLE IF NOT EXISTS notifications (
    id                      SERIAL PRIMARY KEY,
    title                   TEXT NOT NULL,
    message                 TEXT NOT NULL,
    category                TEXT NOT NULL,
    pin_id                  INTEGER REFERENCES pins(id) ON DELETE CASCADE,
    target_neighbourhood_id INTEGER REFERENCES neighbourhoods(id),
    is_read                 BOOLEAN NOT NULL DEFAULT false,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS notifications_created_idx ON notifications (created_at DESC);

COMMIT;
