# Database

PostgreSQL schema, migrations, and synthetic seed data for `mortgage_intel`. Model: [ERD](../docs/architecture/erd.md) · [data dictionary](../docs/architecture/data-dictionary.md).

```text
database/
├── schema/000_roles_and_database.sql   one-time: roles + database (superuser)
├── migrations/                         ordered, idempotent DDL (run as mortgage_owner)
│   ├── 001_core_schema.sql
│   └── 002_query_indexes.sql
├── seed/seed_mortgage_data.sql         synthetic portfolio (re-runnable, dev/test only)
└── scripts/
    ├── reset-dev-db.ps1 / .sh          drop tables → migrations → seed
    └── sample-queries.sql              SQL lab queries + EXPLAIN
```

## Connection settings

Copy [`.env.example`](./.env.example) to `.env` (git-ignored) and set passwords locally. Never commit real values.

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mortgage_intel
POSTGRES_USER=mortgage_app            # runtime role used by services (DML only)
POSTGRES_PASSWORD=<set locally>
POSTGRES_OWNER_USER=mortgage_owner    # migration role (DDL)
POSTGRES_OWNER_PASSWORD=<set locally>
```

## Setup (PowerShell)

Requires PostgreSQL 15+ with `psql` on `PATH`.

```powershell
# 1. One time: roles + database (as superuser). Choose your own local passwords.
psql -U postgres -v owner_password='<owner-pw>' -v app_password='<app-pw>' -f database/schema/000_roles_and_database.sql

# 2. Migrations + seed (re-runnable; drops and recreates domain tables)
$env:POSTGRES_OWNER_PASSWORD = '<owner-pw>'
./database/scripts/reset-dev-db.ps1

# 3. Verify as the app role
$env:PGPASSWORD = '<app-pw>'
psql -U mortgage_app -d mortgage_intel -c "\dt"
psql -U mortgage_app -d mortgage_intel -f database/scripts/sample-queries.sql
```

Bash: `POSTGRES_OWNER_PASSWORD=... ./database/scripts/reset-dev-db.sh`.

To apply migrations by hand instead of the reset script, run each file in order as `mortgage_owner`:

```powershell
psql -U mortgage_owner -d mortgage_intel -f database/migrations/001_core_schema.sql
psql -U mortgage_owner -d mortgage_intel -f database/migrations/002_query_indexes.sql
psql -U mortgage_owner -d mortgage_intel -f database/seed/seed_mortgage_data.sql
```

**Migration rules:** migrations are idempotent (`IF NOT EXISTS`) and wrapped in a transaction. Never edit a merged migration; add `003_*.sql`. The reset script refuses to run against non-local hosts.

## Seed data

All data is **synthetic** (`example.test` emails, `555` phones, invented names). Snapshot date for delinquency figures: **2026-02-24**.

| Table | Rows |
| --- | --- |
| borrower | 8 |
| mortgage | 12 (6 ACTIVE, 3 DELINQUENT, 1 PENDING, 2 CLOSED) |
| loan | 12 |
| payment | 55 |
| servicing_history | 30 |
| delinquency | 3 |
| document | 7 |

Delinquency rate (canonical formula) = 3 / (6 + 3) = **0.3333**.

### Demo IDs

| ID | Scenario |
| --- | --- |
| `BOR-001` | Primary demo borrower (holds `MTG-1001`, `MTG-1003`) |
| `MTG-1001` | **ACTIVE**, on-time payments; loan `LOAN-2001` APPROVED |
| `MTG-1002` | **DELINQUENT**, 45 days past due since 2026-01-10, MODERATE |
| `MTG-1003` | ACTIVE, recently onboarded (first payment due 2026-03-01) |
| `MTG-1004` | ACTIVE, Feb payment 23 days late: **not yet delinquent** (30-day rule edge case) |
| `MTG-1005` | **DELINQUENT**, 85 days past due after an NSF failure, HIGH |
| `MTG-1006`, `MTG-1007` | ACTIVE, on-time payers |
| `MTG-1008` | **DELINQUENT**, 40 days past due, MODERATE |
| `MTG-1009` | PENDING, in underwriting (`LOAN-2009` PENDING) |
| `MTG-1011` | CLOSED, paid off October 2025 |
| `MTG-1012` | ACTIVE, failed and reversed payments cured within grace |
| `MTG-1013` | CLOSED, underwriting DECLINED |

**Delinquent per the 30-day rule:** `MTG-1002`, `MTG-1005`, `MTG-1008`.
**Reserved, not seeded** (used by M4 create-API demos): `BOR-010`, `MTG-1010`, `LOAN-2010`.

### Validation

```sql
SELECT mortgage_external_id, status FROM mortgage WHERE mortgage_external_id IN ('MTG-1001','MTG-1002');
-- MTG-1001 ACTIVE, MTG-1002 DELINQUENT
```
