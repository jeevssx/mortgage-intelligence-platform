-- 004_event_inbox.sql
-- M5: idempotent dedupe table for the servicing-service SQS consumer (docs/architecture/event-catalog.md).
-- Run as mortgage_owner against mortgage_intel. Idempotent: safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS event_inbox (
    event_id     UUID PRIMARY KEY,
    event_type   VARCHAR(50) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMIT;
