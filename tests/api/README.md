# API contract tests

Co-located with each service, same convention as `tests/unit/README.md`:

- `services/mortgage-service/src/test/java/.../controller/` — `BorrowerControllerTest`,
  `MortgageControllerTest`, `PaymentControllerTest`, `AuthControllerTest` (MockMvc)
- `services/servicing-service/src/test/java/.../controller/` — `ServicingControllerTest`
- `analytics/mortgage-analytics-service/tests/test_api.py`
- `ai/mortgage-knowledge-assistant/tests/test_assistant_api.py`

Postman collections (manual exploration, not CI-run): `docs/api/postman/`. OpenAPI contracts:
`docs/api/*.yaml`. The E2E journeys in `tests/e2e/` call these same endpoints over real HTTP,
one layer up from these in-process MockMvc/TestClient tests.
