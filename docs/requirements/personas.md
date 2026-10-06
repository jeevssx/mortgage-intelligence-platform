# Personas

Each persona maps to a security role (from M6) and to the epics in [backlog-epics.md](./backlog-epics.md) that serve them.

---

## 1. Underwriter — "Priya"

| | |
| --- | --- |
| **Role code (M6)** | `UNDERWRITER` |
| **Goals** | Evaluate loan risk against policy; approve or decline loans with a clear rationale; find the relevant guideline quickly. |
| **Pain points** | Policy guidance spread across long PDFs; inconsistent decision records; switching between systems to see borrower and loan details. |
| **Capstone features** | Loan terms and underwriting decision on each mortgage (**Underwriting**); policy Q&A with cited sources (**AI Assistant**); `LoanApproved` events (**Mortgage Management**). |

## 2. Servicing Agent — "Marcus"

| | |
| --- | --- |
| **Role code (M6)** | `SERVICING_AGENT` |
| **Goals** | See current loan status, payment history, and servicing events in one place; post payments correctly; answer borrower calls fast. |
| **Pain points** | History split across systems; duplicate payments when a screen is resubmitted; no single delinquency status. |
| **Capstone features** | Servicing history API (**Servicing**); idempotent payment posting (**Payment**); delinquency status endpoint (**Delinquency**). |

## 3. Risk Analyst — "Elena"

| | |
| --- | --- |
| **Role code (M6)** | `RISK_ANALYST` |
| **Goals** | Track portfolio delinquency trends; identify high-risk borrowers; produce reliable reports for credit committees. |
| **Pain points** | Spreadsheets built from stale extracts; metric definitions that differ by report; slow ad hoc queries. |
| **Capstone features** | Portfolio summary, delinquency report, borrower risk summary, payment trends (**Analytics**); data platform in M8 (**Analytics**). |

## 4. Administrator — "Sam"

| | |
| --- | --- |
| **Role code (M6)** | `ADMIN` |
| **Goals** | Manage users and roles; configure the platform; grant and revoke access promptly. |
| **Pain points** | Manual access requests; no clear view of who has which role; configuration drift between environments. |
| **Capstone features** | User/role management and seed users (**Security**); environment configuration via Terraform and env vars (**Operations**). |

## 5. Security Analyst — "Jordan"

| | |
| --- | --- |
| **Role code (M6)** | read access via `ADMIN` or dedicated audit role |
| **Goals** | See threats and access anomalies; run access reviews; support incident investigations. |
| **Pain points** | Logs without correlation; secrets accidentally committed; no threat model to reason from. |
| **Capstone features** | Trust boundaries and threat model (**Security**); secret scanning in CI (**Security**); correlation IDs in logs and events (**Operations**). |

## 6. Support Engineer — "Taylor"

| | |
| --- | --- |
| **Role code (M6)** | `SUPPORT` |
| **Goals** | Troubleshoot failures quickly; correlate logs across services; follow runbooks to restore service. |
| **Pain points** | Errors without context; inconsistent error formats between services; no health checks. |
| **Capstone features** | Standard error envelope and health endpoints (**Operations**); structured logs with `correlationId` (**Operations**); dashboards and runbooks in M9 (**Operations**). |

## 7. Borrower — "Jamie" (optional, for E2E tests)

| | |
| --- | --- |
| **Role code** | none (external; represented in data and E2E journeys only) |
| **Goals** | Payments credited correctly and promptly; personal data protected. |
| **Pain points** | Misapplied payments; being reported delinquent in error. |
| **Capstone features** | Borrower record (**Borrower Management**); correct payment posting (**Payment**); accurate delinquency rule (**Delinquency**). Demo borrower `BOR-001`. |
