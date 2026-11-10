-- 003_idempotency_record.sql
-- M4: supports Idempotency-Key handling on mortgage-service write endpoints (POST payments).
-- Run as mortgage_owner against mortgage_intel. Idempotent: safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS idempotency_record (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key    VARCHAR(255) NOT NULL,
    request_path       VARCHAR(255) NOT NULL,
    response_reference VARCHAR(255),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_idempotency_key_path UNIQUE (idempotency_key, request_path)
);

COMMIT;
