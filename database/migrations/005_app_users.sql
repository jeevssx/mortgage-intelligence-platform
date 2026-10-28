-- 005_app_users.sql
-- M6: application users for JWT login (mortgage-service POST /api/v1/auth/login).
-- Run as mortgage_owner against mortgage_intel. Idempotent: safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS app_user (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(100) NOT NULL,
    role          VARCHAR(30)  NOT NULL
                  CHECK (role IN ('ADMIN', 'UNDERWRITER', 'SERVICING_AGENT', 'RISK_ANALYST', 'SUPPORT')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMIT;
