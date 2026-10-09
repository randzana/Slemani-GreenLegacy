-- 005_pin_registrations.sql: Volunteer registration / RSVP for tree planting & pins

CREATE TABLE IF NOT EXISTS pin_registrations (
    id                  SERIAL PRIMARY KEY,
    pin_id              INTEGER NOT NULL REFERENCES pins(id) ON DELETE CASCADE,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notes               TEXT,
    status              TEXT NOT NULL DEFAULT 'registered' CHECK (status IN ('registered', 'attended', 'cancelled')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pin_registrations_user_pin_unique UNIQUE (pin_id, user_id)
);

CREATE INDEX IF NOT EXISTS pin_registrations_pin_idx ON pin_registrations (pin_id);
CREATE INDEX IF NOT EXISTS pin_registrations_user_idx ON pin_registrations (user_id);
