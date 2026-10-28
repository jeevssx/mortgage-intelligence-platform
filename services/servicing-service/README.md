# servicing-service

Java 17 / Spring Boot 3 read service for servicing history and delinquency (port **8081**). Reads
`mortgage`, `servicing_history`, and `delinquency`; writes only internal servicing events. See
[ADR-001](../../docs/adr/ADR-001-service-data-ownership.md) for the ownership split with
`mortgage-service`.

## Run locally

Requires the M2 database running and seeded (`database/README.md`).

```bash
cd services/servicing-service
POSTGRES_PASSWORD=<your-local-password> mvn spring-boot:run
curl http://localhost:8081/actuator/health
```

Run tests (in-memory H2, no PostgreSQL needed): `mvn test`.

## API

OpenAPI: [docs/api/servicing-service-openapi.yaml](../../docs/api/servicing-service-openapi.yaml).
Postman: [docs/api/postman/servicing-service.json](../../docs/api/postman/servicing-service.json).

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/api/v1/mortgages/{mortgageExternalId}/servicing-history` | events ordered by `event_time` ascending; 404 if mortgage unknown |
| `GET` | `/api/v1/mortgages/{mortgageExternalId}/delinquency` | 404 if the mortgage has no delinquency row |
| `POST` | `/api/v1/mortgages/{mortgageExternalId}/servicing-events` | internal event ingestion; `eventType=LOAN_DELINQUENT` also publishes `LoanDelinquent` |

### Authentication & RBAC (M6)

Every endpoint requires `Authorization: Bearer <jwt>` minted by `mortgage-service`'s
`POST /api/v1/auth/login` — this service only validates, it has no login endpoint of its own.
`JWT_SECRET` must be identical to `mortgage-service`'s value. RBAC matrix:
[docs/security/security-controls.md](../../docs/security/security-controls.md).

### Lifecycle events (M5)

Polls `SQS_QUEUE_SERVICING_EVENTS` every `SQS_POLL_DELAY_MS` (default 2s) and records each
`eventId` into `event_inbox` (idempotent dedupe) rather than re-deriving `servicing_history` —
see "Why consumers don't duplicate servicing_history" in
[docs/architecture/event-catalog.md](../../docs/architecture/event-catalog.md). If
`SQS_QUEUE_SERVICING_EVENTS` is unset, the poller is disabled (used in tests). Operating the
queue/DLQ: [docs/operations/messaging-runbook.md](../../docs/operations/messaging-runbook.md).

Example (seed data, `database/README.md`):

```bash
curl http://localhost:8081/api/v1/mortgages/MTG-1001/servicing-history
curl http://localhost:8081/api/v1/mortgages/MTG-1002/delinquency
# {"mortgageExternalId":"MTG-1002","status":"DELINQUENT","delinquentSince":"2026-01-10","daysPastDue":45,"severity":"MODERATE"}
```

## Environment

See [.env.example](./.env.example). Same `mortgage_app` database role as `mortgage-service`;
this service never applies DDL.
