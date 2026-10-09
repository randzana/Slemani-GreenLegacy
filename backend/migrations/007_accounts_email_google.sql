-- Accounts: a verified email as the identity, sign-in with Google, a person's household and business
-- ("places", checked by staff, with a monthly money amount), email codes, and phones in one form.
-- For a database created with an earlier schema.sql, without losing its data:
--     psql "$DATABASE_URL" -f migrations/007_accounts_email_google.sql
-- Safe to run again. If two accounts turn out to be one phone written two ways (07501234567 and
-- +9647501234567), it stops, names them and changes nothing: fix those rows by hand, then run it again.
-- (A fresh `python seed.py` already has all of this, and wipes everything.)
BEGIN;

-- 1. users: the verified email of new accounts, and no password for those who only use Google
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;                 -- as written, lower case
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_key TEXT;             -- canonical mailbox (app/emails.py)
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_check;
ALTER TABLE users ADD CONSTRAINT users_email_check CHECK ((email IS NULL) = (email_key IS NULL)
                                                     AND (email IS NULL OR email_verified_at IS NOT NULL));
CREATE UNIQUE INDEX IF NOT EXISTS users_email_key_unique ON users (email_key);   -- one account per mailbox

-- 2. sign-in with Google (Apple later): keyed on the provider's stable subject, never on the email
CREATE TABLE IF NOT EXISTS user_identities (
    id            BIGSERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider      TEXT NOT NULL CHECK (provider IN ('google')),
    subject       TEXT NOT NULL,                     -- Google's "sub"
    email         TEXT,                              -- what Google said at the last sign-in
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ,
    UNIQUE (provider, subject),
    UNIQUE (user_id, provider)                       -- one Google account per person
);

-- 3. a person's household and business: optional, at most one of each, checked by staff before they
-- count. A household's location is private: only its owner and staff ever see it.
CREATE TABLE IF NOT EXISTS places (
    id                  SERIAL PRIMARY KEY,
    owner_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind                TEXT NOT NULL CHECK (kind IN ('household', 'business')),
    name                TEXT NOT NULL CHECK (char_length(btrim(name)) BETWEEN 2 AND 120),
    address             TEXT CHECK (char_length(address) <= 300),
    location            GEOGRAPHY(POINT, 4326) NOT NULL,
    neighbourhood_id    INTEGER REFERENCES neighbourhoods(id),     -- from the location when boundaries are loaded
    residents_count     SMALLINT CHECK (residents_count BETWEEN 1 AND 30),   -- household only
    category            TEXT CHECK (category IN ('restaurant', 'cafe', 'shop', 'supermarket', 'bakery',
                                                 'hotel', 'workshop', 'other')),   -- business only
    license_number      TEXT CHECK (char_length(license_number) <= 64),      -- business only, optional
    verification_status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    verified_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    verified_at         TIMESTAMPTZ,
    rejection_reason    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_id, kind),
    CONSTRAINT places_household_fields CHECK (kind <> 'household'
        OR (residents_count IS NOT NULL AND category IS NULL AND license_number IS NULL)),
    CONSTRAINT places_business_fields CHECK (kind <> 'business'
        OR (category IS NOT NULL AND residents_count IS NULL)),
    CONSTRAINT places_rejection_reason CHECK (verification_status <> 'rejected' OR rejection_reason IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS places_location_idx ON places USING GIST (location);
CREATE INDEX IF NOT EXISTS places_status_idx ON places (verification_status);

-- every change of a place's status, oldest first (places keeps only the latest): staff verifying or
-- rejecting it, and the owner sending it back to the queue by changing its name, category or location
CREATE TABLE IF NOT EXISTS place_reviews (
    id         SERIAL PRIMARY KEY,
    place_id   INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    status     TEXT NOT NULL CHECK (status IN ('pending', 'verified', 'rejected')),
    reason     TEXT,
    changed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS place_reviews_place_idx ON place_reviews (place_id);

-- 4. the monthly money for a verified household or business, one row per place and month. Only a
-- number in the app for now; a digital bank can pay these rows out later.
CREATE TABLE IF NOT EXISTS place_payments (
    id         SERIAL PRIMARY KEY,
    place_id   INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    month      DATE NOT NULL CHECK (extract(day FROM month) = 1),       -- the first day of the month
    amount_iqd INTEGER NOT NULL CHECK (amount_iqd > 0),
    note       TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (place_id, month)
);

-- 5. email codes: only a keyed hash of the code is stored, never the code
CREATE TABLE IF NOT EXISTS otp_codes (
    id            BIGSERIAL PRIMARY KEY,
    email_key     TEXT NOT NULL,                     -- canonical mailbox (app/emails.py)
    purpose       TEXT NOT NULL CHECK (purpose IN ('verify_email')),
    code_hash     TEXT NOT NULL,                     -- HMAC-SHA256(OTP_PEPPER, email_key|purpose|code)
    attempts      SMALLINT NOT NULL DEFAULT 0,
    expires_at    TIMESTAMPTZ NOT NULL,
    consumed_at   TIMESTAMPTZ,
    superseded_at TIMESTAMPTZ,                       -- a newer code was sent
    request_ip    INET,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS otp_codes_email_idx ON otp_codes (email_key, created_at DESC);
CREATE INDEX IF NOT EXISTS otp_codes_ip_idx ON otp_codes (request_ip, created_at DESC);
CREATE INDEX IF NOT EXISTS otp_codes_created_idx ON otp_codes (created_at);
-- at most one live code per mailbox: a resend supersedes the old one in the same transaction
CREATE UNIQUE INDEX IF NOT EXISTS otp_codes_one_live ON otp_codes (email_key, purpose)
    WHERE consumed_at IS NULL AND superseded_at IS NULL;

-- 6. phones in one form (E.164), as app/phones.py writes every new one. Only an Iraqi mobile number
-- has one certain form; any other row is left as it is and named, and that person keeps logging in
-- with exactly what they typed.
CREATE TEMP TABLE phone_fix ON COMMIT DROP AS
    SELECT id, phone, CASE
               WHEN p ~ '^07[3-9][0-9]{8}$'     THEN '+964' || substr(p, 2)
               WHEN p ~ '^7[3-9][0-9]{8}$'      THEN '+964' || p
               WHEN p ~ '^9647[3-9][0-9]{8}$'   THEN '+' || p
               WHEN p ~ '^009647[3-9][0-9]{8}$' THEN '+' || substr(p, 3)
               WHEN p ~ '^\+9647[3-9][0-9]{8}$' THEN p
           END AS normalised
    FROM (SELECT id, phone, regexp_replace(phone, '[[:space:]().-]', '', 'g') AS p FROM users) typed;

DO $$
DECLARE clashes TEXT;
BEGIN
    SELECT string_agg(number || ' = ' || accounts, '; ') INTO clashes FROM (
        SELECT COALESCE(normalised, phone) AS number,
               string_agg('user #' || id || ' "' || phone || '"', ', ' ORDER BY id) AS accounts
        FROM phone_fix GROUP BY 1 HAVING count(*) > 1) same;
    IF clashes IS NOT NULL THEN
        RAISE EXCEPTION 'one phone, several accounts (nothing was changed): %', clashes
            USING HINT = 'Merge or correct these accounts by hand, then run this migration again.';
    END IF;
END $$;

UPDATE users u SET phone = f.normalised
FROM phone_fix f WHERE u.id = f.id AND f.normalised IS NOT NULL AND u.phone <> f.normalised;

DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN SELECT id, phone FROM phone_fix WHERE normalised IS NULL ORDER BY id LOOP
        RAISE NOTICE 'phone left as it is (not an Iraqi mobile number): user #% "%"', r.id, r.phone;
    END LOOP;
END $$;
COMMIT;
