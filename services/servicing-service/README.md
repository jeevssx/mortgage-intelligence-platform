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

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/api/v1/mortgages/{mortgageExternalId}/servicing-history` | events ordered by `event_time` ascending; 404 if mortgage unknown |
| `GET` | `/api/v1/mortgages/{mortgageExternalId}/delinquency` | 404 if the mortgage has no delinquency row |
| `POST` | `/api/v1/mortgages/{mortgageExternalId}/servicing-events` | internal event ingestion (e.g. document upload, future M5 SNS/SQS consumer) |

Example (seed data, `database/README.md`):

```bash
curl http://localhost:8081/api/v1/mortgages/MTG-1001/servicing-history
curl http://localhost:8081/api/v1/mortgages/MTG-1002/delinquency
# {"mortgageExternalId":"MTG-1002","status":"DELINQUENT","delinquentSince":"2026-01-10","daysPastDue":45,"severity":"MODERATE"}
```

## Environment

See [.env.example](./.env.example). Same `mortgage_app` database role as `mortgage-service`;
this service never applies DDL.
