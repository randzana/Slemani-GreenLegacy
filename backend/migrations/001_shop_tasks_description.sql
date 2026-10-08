-- For a database created with the earlier schema.sql, without losing its data:
--     psql "$DATABASE_URL" -f migrations/001_shop_tasks_description.sql
-- (A fresh `python seed.py` already has all of this, and wipes everything.)
BEGIN;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS description_source TEXT;
ALTER TABLE point_ledger ADD COLUMN IF NOT EXISTS detail TEXT;
ALTER TABLE point_ledger DROP CONSTRAINT IF EXISTS point_ledger_kind_check;
ALTER TABLE point_ledger ADD CONSTRAINT point_ledger_kind_check
    CHECK (kind IN ('report', 'confirmation', 'cleanup', 'task', 'redeem'));
CREATE UNIQUE INDEX IF NOT EXISTS point_ledger_task_once ON point_ledger (user_id, detail) WHERE kind = 'task';
COMMIT;
