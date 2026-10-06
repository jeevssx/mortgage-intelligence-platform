-- 001_core_schema.sql
-- Core mortgage domain tables. Matches docs/architecture/erd.md and data-dictionary.md.
-- Run as mortgage_owner against mortgage_intel. Idempotent: safe to re-run.
-- Requires PostgreSQL 13+ (gen_random_uuid() is built in).

BEGIN;

CREATE TABLE IF NOT EXISTS borrower (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    borrower_external_id VARCHAR(20)  NOT NULL UNIQUE
                         CHECK (borrower_external_id ~ '^BOR-[0-9]{3}$'),
    first_name           VARCHAR(100) NOT NULL,
    last_name            VARCHAR(100) NOT NULL,
    email                VARCHAR(255) NOT NULL,
    phone                VARCHAR(30),
    date_of_birth        DATE,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mortgage (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mortgage_external_id VARCHAR(20)   NOT NULL UNIQUE
                         CHECK (mortgage_external_id ~ '^MTG-[0-9]{4}$'),
    borrower_id          UUID          NOT NULL REFERENCES borrower(id),
    status               VARCHAR(30)   NOT NULL
                         CHECK (status IN ('PENDING', 'ACTIVE', 'DELINQUENT', 'CLOSED')),
    original_amount      NUMERIC(15,2) NOT NULL CHECK (original_amount > 0),
    outstanding_balance  NUMERIC(15,2) NOT NULL CHECK (outstanding_balance >= 0),
    origination_date     DATE          NOT NULL,
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_mortgage_balance_le_original CHECK (outstanding_balance <= original_amount)
);

CREATE TABLE IF NOT EXISTS loan (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_external_id      VARCHAR(20)  NOT NULL UNIQUE
                          CHECK (loan_external_id ~ '^LOAN-[0-9]{4}$'),
    mortgage_id           UUID         NOT NULL UNIQUE REFERENCES mortgage(id),
    interest_rate         NUMERIC(6,4) NOT NULL CHECK (interest_rate > 0 AND interest_rate < 1),
    term_months           INT          NOT NULL CHECK (term_months BETWEEN 1 AND 480),
    underwriting_decision VARCHAR(20)  NOT NULL DEFAULT 'PENDING'
                          CHECK (underwriting_decision IN ('PENDING', 'APPROVED', 'DECLINED')),
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mortgage_id UUID          NOT NULL REFERENCES mortgage(id),
    due_date    DATE          NOT NULL,
    paid_date   DATE,
    amount      NUMERIC(15,2) NOT NULL CHECK (amount > 0),
    status      VARCHAR(20)   NOT NULL
                CHECK (status IN ('SCHEDULED', 'POSTED', 'FAILED', 'REVERSED')),
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_payment_posted_has_paid_date CHECK (status <> 'POSTED' OR paid_date IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS servicing_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mortgage_id UUID        NOT NULL REFERENCES mortgage(id),
    event_time  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type  VARCHAR(50) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS delinquency (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mortgage_id      UUID        NOT NULL UNIQUE REFERENCES mortgage(id),
    delinquent_since DATE        NOT NULL,
    days_past_due    INT         NOT NULL CHECK (days_past_due >= 0),
    severity         VARCHAR(20) NOT NULL DEFAULT 'MODERATE'
                     CHECK (severity IN ('LOW', 'MODERATE', 'HIGH', 'SEVERE'))
);

CREATE TABLE IF NOT EXISTS document (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mortgage_id   UUID         NOT NULL REFERENCES mortgage(id),
    document_type VARCHAR(50)  NOT NULL,
    s3_key        VARCHAR(512) UNIQUE,
    file_name     VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mortgage_borrower       ON mortgage(borrower_id);
CREATE INDEX IF NOT EXISTS idx_mortgage_status         ON mortgage(status);
CREATE INDEX IF NOT EXISTS idx_payment_mortgage_due    ON payment(mortgage_id, due_date);
CREATE INDEX IF NOT EXISTS idx_servicing_mortgage_time ON servicing_history(mortgage_id, event_time);
CREATE INDEX IF NOT EXISTS idx_document_mortgage       ON document(mortgage_id);

COMMIT;
