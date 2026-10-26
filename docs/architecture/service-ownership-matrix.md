# Service ownership matrix (M5)

Decomposition rationale: [ADR-002](../adr/ADR-002-microservice-decomposition.md). Data ownership
baseline: [ADR-001](../adr/ADR-001-service-data-ownership.md).

| Service | Port | Tables (writes) | Tables (reads only) | APIs owned | Events produced | Events consumed |
| --- | --- | --- | --- | --- | --- | --- |
| `mortgage-service` | 8080 | `borrower`, `mortgage`, `loan`, `payment`, `servicing_history` (onboarding/payment rows only), `idempotency_record` | — | `/api/v1/borrowers`, `/api/v1/mortgages`, `/api/v1/mortgages/{id}/payments` | `MortgageCreated`, `LoanApproved`, `PaymentReceived`, `PaymentMissed` | — |
| `servicing-service` | 8081 | `servicing_history` (internal events only), `event_inbox` | `mortgage` (status), `delinquency` | `/api/v1/mortgages/{id}/servicing-history`, `/api/v1/mortgages/{id}/delinquency`, `/api/v1/mortgages/{id}/servicing-events` | `LoanDelinquent` | `capstone-mortgage-servicing-dev` (all four mortgage-service events) |
| `mortgage-analytics-service` | 8000 | `document` | `borrower`, `mortgage`, `payment`, `delinquency` | `/api/v1/analytics/*`, `/api/v1/documents/upload` | — | `capstone-mortgage-analytics-dev` (reserved, not yet wired) |

## No cyclic dependencies

Both Java services connect to PostgreSQL directly (shared database, per ADR-001) and communicate
with each other **only** through the SNS topic — there is no synchronous service-to-service HTTP
call in either direction. `mortgage-analytics-service` is a pure reader of the same database plus
its own S3/SNS integration from M3; it does not call either Java service.

## Consumer-driven contract note

`servicing-service` depends on `mortgage-service` for exactly one thing: the shape of
`mortgage_external_id` (`MTG-####`, [standards.md](https://github.com/UID-Technologies/capstone-secondary-mortgage-intelligence-platform/blob/main/guides/standards.md))
appearing in both the `mortgage` table and every event `payload.mortgageExternalId`. Any change to
that ID format is a breaking change for `servicing-service` and must be called out in an ADR
before `mortgage-service` ships it.
