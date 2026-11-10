# Security tests (M6)

Automated auth/RBAC tests live **inside each service** (same placement convention as the API
tests added in M4), not duplicated here:

- `services/mortgage-service/src/test/java/com/capstone/mortgage/controller/AuthControllerTest.java`
  — real login → JWT → protected-endpoint flow (no `@WithMockUser`); wrong password; missing
  token; tampered token.
- `services/mortgage-service/src/test/java/com/capstone/mortgage/controller/RbacTest.java` —
  every role against `POST /mortgages` and `POST .../payments`.
- `services/servicing-service/src/test/java/com/capstone/servicing/security/JwtValidationServiceTest.java`
  and `services/mortgage-service/.../security/JwtServiceTest.java` — fail-fast behavior for the
  insecure default JWT secret outside dev/test profiles (see V-2 in
  [vulnerability-report.md](../../docs/security/vulnerability-report.md)).
- `services/servicing-service/src/test/java/com/capstone/servicing/controller/RbacTest.java` —
  every role against `POST .../servicing-events`.

Run with `mvn test` in either service directory.

## Manual pentest exercise log

The live checks run against real running instances during M6 (not covered by the automated
suite above, since they involve cross-service and infra-level behavior) are recorded directly
in [docs/security/vulnerability-report.md](../../docs/security/vulnerability-report.md):

- Cross-service JWT validation (mortgage-service issues, servicing-service validates with an
  independently-configured copy of the same shared secret).
- SQL-injection-style payload in a path variable → confirmed parameterized, no leak (V-3).
- Rate limiting on `/api/v1/auth/login` → confirmed `429` after 10 requests/60s (V-4 notes the
  gap: not applied elsewhere).
- SCA image scan (Trivy) → V-6.

Re-run the live checks with the curl commands embedded in
[security-controls.md](../../docs/security/security-controls.md) and
[vulnerability-report.md](../../docs/security/vulnerability-report.md) against a locally running
stack (`docker compose up --build -d` or `mvn spring-boot:run` in each service).
