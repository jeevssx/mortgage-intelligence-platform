# Unit tests

Co-located in each service/component, same placement convention as `tests/security/README.md`:

- `services/mortgage-service/src/test/java/` — 30 tests (JUnit 5 + MockMvc)
- `services/servicing-service/src/test/java/` — 16 tests
- `analytics/mortgage-analytics-service/tests/` — pytest
- `ai/mortgage-knowledge-assistant/tests/` — 16 tests (pytest)
- `infrastructure/aws/lambda/doc-processor/tests/` — 5 tests (pytest + moto)
- `infrastructure/data-pipeline/tests/` — 4 tests (pytest + moto)

Run each with that language's standard command (`mvn test` / `pytest -v`) from the
component's own directory. CI runs all of them in the `unit_test` stage
(`docs/operations/cicd.md`).
