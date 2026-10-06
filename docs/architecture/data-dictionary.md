# Data Dictionary

Database: `mortgage_intel` (PostgreSQL 15+). DDL: [`database/migrations/`](../../database/migrations/). Diagram: [erd.md](./erd.md).

Conventions: primary keys are `UUID` defaulting to `gen_random_uuid()`; money is `NUMERIC(15,2)`; timestamps are `TIMESTAMPTZ` (UTC); enums are `VARCHAR` with `CHECK` constraints so values can be extended by migration.

---

## borrower

Party on the loan. **Contains PII** (synthetic only in this project).

| Column | Type | Null | Constraints / notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | **PK** |
| `borrower_external_id` | VARCHAR(20) | NO | **UNIQUE**; CHECK format `^BOR-[0-9]{3}$` |
| `first_name` | VARCHAR(100) | NO | PII |
| `last_name` | VARCHAR(100) | NO | PII |
| `email` | VARCHAR(255) | NO | PII; seed uses `example.test` |
| `phone` | VARCHAR(30) | YES | PII; seed uses `+1-555-xxxx` |
| `date_of_birth` | DATE | YES | PII |
| `created_at` | TIMESTAMPTZ | NO | DEFAULT `NOW()` |

**Relationships:** 1 borrower → 0..N `mortgage`.
**Indexes:** PK; UNIQUE on `borrower_external_id`; `idx_borrower_email_lower` on `lower(email)` (migration 002, case-insensitive lookup).

## mortgage

Servicing unit: balance and lifecycle status.

| Column | Type | Null | Constraints / notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | **PK** |
| `mortgage_external_id` | VARCHAR(20) | NO | **UNIQUE**; CHECK format `^MTG-[0-9]{4}$` |
| `borrower_id` | UUID | NO | **FK** → `borrower.id` |
| `status` | VARCHAR(30) | NO | CHECK in (`PENDING`, `ACTIVE`, `DELINQUENT`, `CLOSED`) |
| `original_amount` | NUMERIC(15,2) | NO | CHECK `> 0` |
| `outstanding_balance` | NUMERIC(15,2) | NO | CHECK `>= 0` and `<= original_amount` |
| `origination_date` | DATE | NO | |
| `created_at` | TIMESTAMPTZ | NO | DEFAULT `NOW()` |

**Relationships:** N:1 `borrower`; 1:1 `loan`; 1:N `payment`, `servicing_history`, `document`; 1:0..1 `delinquency`.
**Indexes:** `idx_mortgage_borrower (borrower_id)` for borrower portfolios; `idx_mortgage_status (status)` for delinquency reports and status queues.

**Status rules:** `PENDING` until underwriting decides → `ACTIVE` when approved / `CLOSED` when declined. `ACTIVE` → `DELINQUENT` when an installment is unpaid 30+ days after `due_date`; back to `ACTIVE` when cured. `CLOSED` on payoff.

## loan

Underwriting terms and decision, 1:1 with mortgage.

| Column | Type | Null | Constraints / notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | **PK** |
| `loan_external_id` | VARCHAR(20) | NO | **UNIQUE**; CHECK format `^LOAN-[0-9]{4}$` |
| `mortgage_id` | UUID | NO | **FK** → `mortgage.id`; **UNIQUE** (enforces 1:1) |
| `interest_rate` | NUMERIC(6,4) | NO | Decimal fraction (0.0625 = 6.25%); CHECK `> 0 AND < 1` |
| `term_months` | INT | NO | CHECK 1–480 |
| `underwriting_decision` | VARCHAR(20) | NO | DEFAULT `PENDING`; CHECK in (`PENDING`, `APPROVED`, `DECLINED`) |
| `created_at` | TIMESTAMPTZ | NO | DEFAULT `NOW()` |

**Indexes:** PK; UNIQUE on `loan_external_id` and `mortgage_id`.

## payment

Scheduled installments and payment attempts. One installment (`due_date`) can have several rows (e.g. `FAILED` then `POSTED`).

| Column | Type | Null | Constraints / notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | **PK** |
| `mortgage_id` | UUID | NO | **FK** → `mortgage.id` |
| `due_date` | DATE | NO | Installment due date |
| `paid_date` | DATE | YES | Required when `status = 'POSTED'` (CHECK `chk_payment_posted_has_paid_date`) |
| `amount` | NUMERIC(15,2) | NO | CHECK `> 0` |
| `status` | VARCHAR(20) | NO | CHECK in (`SCHEDULED`, `POSTED`, `FAILED`, `REVERSED`) |
| `created_at` | TIMESTAMPTZ | NO | DEFAULT `NOW()` |

**Indexes:** `idx_payment_mortgage_due (mortgage_id, due_date)` for payment timelines; `idx_payment_open_due (due_date, mortgage_id) WHERE status IN ('SCHEDULED','FAILED')` (migration 002) for the delinquency batch. See [query-notes.md](./query-notes.md).

**Business rules:** an installment is **paid** when a `POSTED` row exists for that `mortgage_id` + `due_date`. **On time** = `paid_date <= due_date + 15 days` (grace period). An installment unpaid 30+ days after `due_date` makes the mortgage `DELINQUENT`.

## servicing_history

Append-only, chronological log of servicing events.

| Column | Type | Null | Constraints / notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | **PK** |
| `mortgage_id` | UUID | NO | **FK** → `mortgage.id` |
| `event_time` | TIMESTAMPTZ | NO | DEFAULT `NOW()` |
| `event_type` | VARCHAR(50) | NO | See values below |
| `description` | TEXT | YES | Human-readable; must not contain PII beyond business IDs |

**Event types in use:** `APPLICATION_RECEIVED`, `UNDERWRITING_DECLINED`, `ONBOARDING_COMPLETE`, `PAYMENT_POSTED`, `PAYMENT_FAILED`, `PAYMENT_REVERSED`, `PAYMENT_MISSED`, `STATUS_CHANGED`, `DELINQUENCY_UPDATED`, `BORROWER_CONTACT`, `LOAN_PAID_OFF`. Not CHECK-constrained so new event types (M5) don't need a migration; validated in the service layer.
**Indexes:** `idx_servicing_mortgage_time (mortgage_id, event_time)` for the chronological servicing history API.

## delinquency

Current delinquency snapshot: at most one row per mortgage, present only while delinquent.

| Column | Type | Null | Constraints / notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | **PK** |
| `mortgage_id` | UUID | NO | **FK** → `mortgage.id`; **UNIQUE** |
| `delinquent_since` | DATE | NO | Due date of the oldest unpaid installment |
| `days_past_due` | INT | NO | CHECK `>= 0`; days from `delinquent_since` to the snapshot date |
| `severity` | VARCHAR(20) | NO | DEFAULT `MODERATE`; CHECK in (`LOW`, `MODERATE`, `HIGH`, `SEVERE`) |

**Severity bands:** `LOW` < 30 (early, mortgage still `ACTIVE`; reserved), `MODERATE` 30–59, `HIGH` 60–89, `SEVERE` 90+.
**Indexes:** UNIQUE on `mortgage_id` (also serves lookups).

## document

Metadata for files stored in S3. Binaries are never stored in the database.

| Column | Type | Null | Constraints / notes |
| --- | --- | --- | --- |
| `id` | UUID | NO | **PK**; returned to clients as `documentId` |
| `mortgage_id` | UUID | NO | **FK** → `mortgage.id` |
| `document_type` | VARCHAR(50) | NO | e.g. `INCOME_VERIFICATION`, `APPRAISAL`, `CLOSING_DISCLOSURE`, `HARDSHIP_LETTER`, `LIEN_RELEASE` |
| `s3_key` | VARCHAR(512) | YES | **UNIQUE**; `mortgages/{MTG-####}/{uuid}-{fileName}`; NULL only if upload pending |
| `file_name` | VARCHAR(255) | NO | Must not contain PII |
| `created_at` | TIMESTAMPTZ | NO | DEFAULT `NOW()` |

**Indexes:** `idx_document_mortgage (mortgage_id)` for document lists.

---

## Roles and privileges

| Role | Privileges | Used by |
| --- | --- | --- |
| `mortgage_owner` | Owns database and `public` schema; DDL | Migrations, seed, reset script |
| `mortgage_app` | `SELECT, INSERT, UPDATE, DELETE` on tables (via default privileges); no DDL | Services at runtime |

Created by [`database/schema/000_roles_and_database.sql`](../../database/schema/000_roles_and_database.sql).
