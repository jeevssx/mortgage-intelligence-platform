# mortgage-service

Java 17 / Spring Boot 3 service for borrower, mortgage, and payment CRUD (port **8080**). Writes
`borrower`, `mortgage`, `loan`, `payment`, and the `servicing_history` events it generates as a
side effect — see [ADR-001](../../docs/adr/ADR-001-service-data-ownership.md) for the data
ownership split with `servicing-service`.

## Run locally

Requires the M2 database running and seeded (`database/README.md`).

```powershell
cd services/mortgage-service
Copy-Item .env.example .env   # set POSTGRES_PASSWORD to your mortgage_app password
$env:POSTGRES_PASSWORD = '<your-local-password>'
mvn spring-boot:run
curl http://localhost:8080/actuator/health
```

Bash:

```bash
cd services/mortgage-service
POSTGRES_PASSWORD=<your-local-password> mvn spring-boot:run
```

Run tests (uses an in-memory H2 database, no PostgreSQL needed):

```bash
mvn test
```

## API

All endpoints are under `/api/v1`. OpenAPI: [docs/api/mortgage-service-openapi.yaml](../../docs/api/mortgage-service-openapi.yaml).
Postman: [docs/api/postman/mortgage-service.json](../../docs/api/postman/mortgage-service.json).
Full examples in [reference/sample-api-contracts.md](https://github.com/UID-Technologies/capstone-secondary-mortgage-intelligence-platform/blob/main/reference/sample-api-contracts.md).

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/api/v1/borrowers` | 201, 409 if `borrowerExternalId` exists |
| `GET` | `/api/v1/borrowers/{borrowerExternalId}` | 404 if unknown |
| `POST` | `/api/v1/mortgages` | 201; optional nested `loan`; 404 if borrower unknown |
| `GET` | `/api/v1/mortgages/{mortgageExternalId}` | includes loan if present |
| `GET` | `/api/v1/mortgages?borrowerId=&page=&size=` | paginated |
| `POST` | `/api/v1/mortgages/{mortgageExternalId}/payments` | transactional; see below |
| `GET` | `/api/v1/mortgages/{mortgageExternalId}/payments?page=&size=` | paginated, newest `dueDate` first |

### Payment transaction

`POST .../payments` runs as one `@Transactional` method
(`PaymentServiceImpl.postPayment`):

1. Insert the `payment` row.
2. Apply the balance effect for `status`: `POSTED` subtracts `amount` (floored at 0),
   `REVERSED` adds it back (capped at `original_amount`), `SCHEDULED`/`FAILED` have no effect.
3. Insert a `servicing_history` row (`PAYMENT_POSTED` / `PAYMENT_REVERSED` / `PAYMENT_FAILED` /
   `PAYMENT_SCHEDULED`).
4. If an `Idempotency-Key` header is present, record it in `idempotency_record`; a repeat of the
   same key on the same path returns `409 DUPLICATE_REQUEST` instead of double-posting.

This service does **not** recompute `delinquency` rows — see ADR-001.

### Lifecycle events (M5)

Publishes `MortgageCreated` and `LoanApproved` on mortgage creation, `PaymentReceived` /
`PaymentMissed` on payment posting, to the SNS topic in `SNS_TOPIC_MORTGAGE_EVENTS`. If that
variable is unset, publishing is a silent no-op (used in tests and any environment without the
event backbone). Catalog and schemas: [docs/architecture/event-catalog.md](../../docs/architecture/event-catalog.md).
Publish failures are logged at `ERROR` and never fail the HTTP request — see ADR-002.

### Errors

Standard envelope (`code`, `message`, `correlationId`, `timestamp`); validation failures return
`400 VALIDATION_FAILED`, missing resources `404`, duplicates `409`. `X-Correlation-Id` is read
from the request or generated, echoed on the response, and bound to log lines via MDC.

## Environment

See [.env.example](./.env.example). `POSTGRES_*` must match the `mortgage_app` role from
`database/schema/000_roles_and_database.sql`.
