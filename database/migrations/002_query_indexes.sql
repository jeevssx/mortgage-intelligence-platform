-- 002_query_indexes.sql
-- Indexes justified by the query analysis in database/scripts/sample-queries.sql
-- and docs/architecture/query-notes.md. Idempotent.

BEGIN;

-- Delinquency batch: "unpaid installments past their due date".
-- Partial index: only open installments are indexed, so it stays small as POSTED history grows.
CREATE INDEX IF NOT EXISTS idx_payment_open_due
    ON payment(due_date, mortgage_id)
    WHERE status IN ('SCHEDULED', 'FAILED');

-- Servicing agent search by borrower email (case-insensitive).
CREATE INDEX IF NOT EXISTS idx_borrower_email_lower
    ON borrower(lower(email));

COMMIT;
