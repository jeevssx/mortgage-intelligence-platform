# Sprint Plans

Sprints are one week, aligned with milestones. Story details are in [user-stories.md](./user-stories.md). The GitHub issue board mirrors these IDs (one issue per story, labeled `sprint-1` / `sprint-2` and by epic).

---

## Sprint 1 — Data model and foundational read paths

**Dates:** Weeks 2–3 (M2 + M3)
**Sprint goal:** A reproducible database with realistic synthetic data, and the first read paths over it (analytics), so that M4 services can be built on a stable model.

| Story | Title | Epic | Persona | Points | Milestone |
| --- | --- | --- | --- | --- | --- |
| US-SEC-002 | Block secrets in the repository | Security | Security Analyst | 2 | M2 |
| US-OPS-003 | CI pipeline gates (migrations) | Operations | Support Engineer | 3 | M2 |
| US-DEL-002 | Apply the 30-day delinquency rule (data model + seed scenarios) | Delinquency | Risk Analyst | 3 | M2 |
| US-OPS-001 | Health endpoints | Operations | Support Engineer | 1 | M3 |
| US-OPS-002 | Correlated structured logs | Operations | Support Engineer | 2 | M3 |
| US-ANL-001 | Portfolio summary | Analytics | Risk Analyst | 3 | M3 |
| US-ANL-002 | Delinquency report | Analytics | Risk Analyst | 2 | M3 |
| US-ANL-003 | Borrower risk summary | Analytics | Risk Analyst | 2 | M3 |
| US-ANL-004 | Payment trends | Analytics | Risk Analyst | 3 | M3 |
| US-DOC-001 | Upload mortgage document | Document Management | Underwriter | 5 | M3 |

**Committed:** 26 points.

**Tasks outside stories:** ERD and data dictionary, migrations 001–002, seed data, sample queries, branch protection.

**Definition of done:** migrations and seed apply cleanly in CI; analytics endpoints match SQL aggregates; `pytest` passes; docs merged to `develop`.

---

## Sprint 2 — Core write paths: borrowers, mortgages, payments, servicing, delinquency

**Dates:** Weeks 4–5 (M4)
**Sprint goal:** Java services expose the mortgage lifecycle write paths and servicing reads, using the Sprint 1 data model.

| Story | Title | Epic | Persona | Points |
| --- | --- | --- | --- | --- |
| US-BOR-001 | Create borrower | Borrower Management | Servicing Agent | 2 |
| US-BOR-002 | Get borrower | Borrower Management | Servicing Agent | 1 |
| US-MTG-001 | Create mortgage | Mortgage Management | Underwriter | 3 |
| US-MTG-002 | Get mortgage | Mortgage Management | Servicing Agent | 2 |
| US-UW-001 | Record underwriting decision | Underwriting | Underwriter | 3 |
| US-PAY-001 | Post payment (idempotent) | Payment | Servicing Agent | 5 |
| US-PAY-002 | List payments | Payment | Servicing Agent | 2 |
| US-SRV-001 | Retrieve servicing history | Servicing | Servicing Agent | 2 |
| US-DEL-001 | Get delinquency status | Delinquency | Servicing Agent | 2 |
| US-DEL-002 | Apply the 30-day delinquency rule (batch in service) | Delinquency | Risk Analyst | 5 |

**Committed:** 27 points.

**Stretch:** US-PAY-003, US-SRV-002, US-MTG-003, US-UW-002.

---

## Later backlog (not yet scheduled)

| Story | Target milestone |
| --- | --- |
| US-BOR-003, US-DOC-002 | M4 (stretch) |
| US-SRV-003, US-DEL-003 | M5 |
| US-SEC-001, US-SEC-003 | M6 |
| US-AI-001, US-AI-002 | M7 |
