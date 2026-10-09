-- GreenLegacy Slemani (practice build) — PostgreSQL + PostGIS schema
-- Six tables, as in the build plan. Locations are PostGIS geography points (metres for distances).

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS pin_registrations, notifications, pins, point_ledger, cleanups, challenges, reports, users, neighbourhoods CASCADE;

CREATE TABLE neighbourhoods (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    -- optional; loaded from a GeoJSON export by tools/import_boundaries.py. MULTIPOLYGON because
    -- OSM areas often come in several parts (a single polygon is stored as a one-part multipolygon)
    boundary    GEOGRAPHY(MULTIPOLYGON, 4326)
);
CREATE INDEX neighbourhoods_boundary_idx ON neighbourhoods USING GIST (boundary);

CREATE TABLE users (
    id               SERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    phone            TEXT NOT NULL UNIQUE,         -- one account per phone number
    password_hash    TEXT NOT NULL,
    neighbourhood_id INTEGER REFERENCES neighbourhoods(id),
    role             TEXT NOT NULL DEFAULT 'citizen' CHECK (role IN ('citizen', 'staff')),
    trust_level      INTEGER NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
    id                 SERIAL PRIMARY KEY,
    reporter_id        INTEGER NOT NULL REFERENCES users(id),
    location           GEOGRAPHY(POINT, 4326) NOT NULL,
    photo_path         TEXT NOT NULL,
    photo_hash         BIGINT NOT NULL,            -- 64-bit perceptual hash (pHash)
    litter_count       INTEGER NOT NULL,
    litter_classes     JSONB NOT NULL DEFAULT '{}'::jsonb,
    coverage           REAL NOT NULL DEFAULT 0,    -- share of the image covered by litter boxes
    dirtiness          INTEGER NOT NULL CHECK (dirtiness BETWEEN 1 AND 5),
    description        TEXT,                       -- plain Kurdish summary for crews (app/ai/describe.py)
    description_source TEXT,                       -- 'template' (offline) or 'claude' (vision model)
    status             TEXT NOT NULL DEFAULT 'open'
                       CHECK (status IN ('open', 'in_progress', 'clean', 'needs_review', 'confirmation')),
    confirms_report_id INTEGER REFERENCES reports(id),   -- set when this row only confirms an earlier report
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    cleaned_at         TIMESTAMPTZ
);
CREATE INDEX reports_location_idx ON reports USING GIST (location);
CREATE INDEX reports_status_idx ON reports (status);

CREATE TABLE challenges (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    report_id        INTEGER NOT NULL REFERENCES reports(id),
    instruction      TEXT NOT NULL,                -- machine code, e.g. qr_first / qr_last
    instruction_text TEXT NOT NULL,                -- what the phone shows, in Kurdish
    issued_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at       TIMESTAMPTZ NOT NULL,
    used             BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE cleanups (
    id                  SERIAL PRIMARY KEY,
    report_id           INTEGER NOT NULL REFERENCES reports(id),
    cleaner_id          INTEGER NOT NULL REFERENCES users(id),
    challenge_id        INTEGER REFERENCES challenges(id),
    location            GEOGRAPHY(POINT, 4326),
    frame_paths         JSONB NOT NULL DEFAULT '[]'::jsonb,
    after_frame_path    TEXT,                      -- the frame that best shows the cleaned spot
    frame_hashes        BIGINT[] NOT NULL DEFAULT '{}',
    litter_count_before INTEGER,
    litter_count_after  INTEGER,
    similarity          REAL,                      -- ORB inlier count against the before photo
    verdict             TEXT NOT NULL CHECK (verdict IN ('verified', 'review', 'rejected')),
    reason_code         TEXT,
    reason              TEXT,
    reviewed_by         INTEGER REFERENCES users(id),
    reviewed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE point_ledger (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      INTEGER NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('report', 'confirmation', 'cleanup', 'task', 'redeem', 'bin_disposal')),
    status      TEXT NOT NULL CHECK (status IN ('pending', 'released', 'revoked')),
    report_id   INTEGER REFERENCES reports(id),
    cleanup_id  INTEGER REFERENCES cleanups(id),
    bin_id      INTEGER,
    release_at  TIMESTAMPTZ,                       -- NULL = waits for an event (confirmation, review)
    detail      TEXT,                              -- task: 'task:<code>:<day>'; redeem: reward code + voucher
    honoured_at TIMESTAMPTZ,                       -- redeem: when staff handed the reward over (once)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX point_ledger_user_idx ON point_ledger (user_id);
-- a daily task bonus can be claimed once per person per day
CREATE UNIQUE INDEX point_ledger_task_once ON point_ledger (user_id, detail) WHERE kind = 'task';

CREATE TABLE pins (
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
CREATE INDEX pins_location_idx ON pins USING GIST (location);
CREATE INDEX pins_status_idx ON pins (status);

CREATE TABLE notifications (
    id                      SERIAL PRIMARY KEY,
    title                   TEXT NOT NULL,
    message                 TEXT NOT NULL,
    category                TEXT NOT NULL,
    pin_id                  INTEGER REFERENCES pins(id) ON DELETE CASCADE,
    target_neighbourhood_id INTEGER REFERENCES neighbourhoods(id),
    is_read                 BOOLEAN NOT NULL DEFAULT false,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX notifications_created_idx ON notifications (created_at DESC);

CREATE TABLE pin_registrations (
    id                  SERIAL PRIMARY KEY,
    pin_id              INTEGER NOT NULL REFERENCES pins(id) ON DELETE CASCADE,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notes               TEXT,
    status              TEXT NOT NULL DEFAULT 'registered' CHECK (status IN ('registered', 'attended', 'cancelled')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pin_registrations_user_pin_unique UNIQUE (pin_id, user_id)
);
CREATE INDEX pin_registrations_pin_idx ON pin_registrations (pin_id);
CREATE INDEX pin_registrations_user_idx ON pin_registrations (user_id);

CREATE TABLE trash_bins (
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
CREATE INDEX trash_bins_location_idx ON trash_bins USING GIST (location);
CREATE INDEX trash_bins_code_idx ON trash_bins (code);

CREATE TABLE bin_disposals (
    id               SERIAL PRIMARY KEY,
    bin_id           INTEGER NOT NULL REFERENCES trash_bins(id) ON DELETE CASCADE,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    points_awarded   INTEGER NOT NULL DEFAULT 15,
    location         GEOGRAPHY(POINT, 4326),
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX bin_disposals_bin_idx ON bin_disposals (bin_id);
CREATE INDEX bin_disposals_user_idx ON bin_disposals (user_id);


