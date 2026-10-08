-- For a database created before vouchers could be marked as handed over:
--     psql "$DATABASE_URL" -f migrations/003_voucher_honoured.sql
-- (A fresh `python seed.py` already has this, and wipes everything.)
ALTER TABLE point_ledger ADD COLUMN IF NOT EXISTS honoured_at TIMESTAMPTZ;
