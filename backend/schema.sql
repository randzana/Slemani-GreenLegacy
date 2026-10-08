-- GreenLegacy Slemani (practice build) — PostgreSQL + PostGIS schema
-- Six tables, as in the build plan. Locations are PostGIS geography points (metres for distances).

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS point_ledger, cleanups, challenges, reports, users, neighbourhoods CASCADE;

CREATE TABLE neighbourhoods (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    boundary    GEOGRAPHY(POLYGON, 4326)          -- optional on day one
);

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
    kind        TEXT NOT NULL CHECK (kind IN ('report', 'confirmation', 'cleanup', 'redeem')),
    status      TEXT NOT NULL CHECK (status IN ('pending', 'released', 'revoked')),
    report_id   INTEGER REFERENCES reports(id),
    cleanup_id  INTEGER REFERENCES cleanups(id),
    release_at  TIMESTAMPTZ,                       -- NULL = waits for an event (confirmation, review)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX point_ledger_user_idx ON point_ledger (user_id);
