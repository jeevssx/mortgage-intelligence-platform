# Threat model (STRIDE) — M6

Scope: `mortgage-service`, `servicing-service`, the SNS/SQS event backbone (M5), and the
PostgreSQL datastore. Trust boundaries reference
[docs/architecture/deployment-architecture.md](../architecture/deployment-architecture.md) and
[docs/architecture/trust-boundaries.md](../architecture/trust-boundaries.md). Architecture:
[service-ownership-matrix.md](../architecture/service-ownership-matrix.md).

## System diagram (trust boundaries)

```text
[Internet / client]
      │  (1) Internet → App boundary
      ▼
[mortgage-service :8080] ──(2) App → Data──> [PostgreSQL mortgage_intel]
      │  (3) App → Messaging
      ▼
[SNS capstone-mortgage-lifecycle-dev]
      │
      ▼
[SQS capstone-mortgage-servicing-dev] ──(3)──> [servicing-service :8081] ──(2)──> [PostgreSQL]
      │ (after 3 failed receives)
      ▼
[DLQ capstone-mortgage-servicing-dlq-dev]
```

## STRIDE analysis

| # | Threat category | Scenario | Boundary | Mitigation | Status |
| --- | --- | --- | --- | --- | --- |
| T1 | **Spoofing** | Attacker submits requests without a valid identity to a mutating endpoint | (1) Internet → App | JWT required on every endpoint except `/auth/login` and `/actuator/health`; `anyRequest().authenticated()` default | Mitigated |
| T2 | **Spoofing** | Attacker forges/replays an old JWT after it expires | (1) Internet → App | `exp` claim checked on every parse (`JwtService`/`JwtValidationService`); 3600s TTL | Mitigated |
| T3 | **Tampering** | Attacker modifies JWT payload (e.g. elevates own role) in transit | (1) Internet → App | HS256 signature verification rejects any payload change (`Jwts.parser().verifyWith(key)`); verified in `AuthControllerTest.protectedEndpoint_withTamperedToken_returns401` | Mitigated |
| T4 | **Tampering** | SQL injection via mortgage/borrower external IDs | (2) App → Data | 100% parameterized JPA queries; verified live with a `' OR '1'='1` payload → clean 404, no SQL error leak | Mitigated |
| T5 | **Tampering** | Forged/replayed lifecycle event injected directly into the SQS queue | (3) App → Messaging | `servicing-service` dedupes by `eventId` in `event_inbox`; a malformed event (no `eventId`/`eventType`) throws and is retried-then-DLQ'd rather than silently accepted. **Not mitigated:** no message-level signing — anyone with LocalStack/AWS credentials to the queue can publish an event mortgage-service didn't send | Partially mitigated — see R-4 |
| T6 | **Repudiation** | A role-restricted action is performed and later disputed | (1)/(2) | `X-Correlation-Id` + structured logs (`guides/standards.md`) tie every request to a username (JWT `sub`) and timestamp; no write endpoint allows anonymous access | Mitigated |
| T7 | **Information disclosure** | Stack trace or internal state leaked in an error response | (1) Internet → App | `GlobalExceptionHandler`'s catch-all returns a fixed `INTERNAL_ERROR` message, never `ex.getMessage()` or a stack trace, for unhandled exceptions | Mitigated |
| T8 | **Information disclosure** | Password or JWT written to logs | (1)/(2) | `AuthServiceImpl` logs only username + outcome, never the password or token; verified by code review (no `log.*(token)` or `log.*(password)` call exists in either service) | Mitigated |
| T9 | **Information disclosure** | Credentials/secrets committed to Git | (1)/(2)/(3) | `.env.example` only, `.gitignore` excludes `.env`; secret scanning (gitleaks) in CI since M2 | Mitigated |
| T10 | **Denial of service** | Credential-stuffing or brute-force against `/auth/login` | (1) Internet → App | `RateLimitFilter`: 10 req/60s per client IP on the login path only; verified live (11th rapid attempt → `429 RATE_LIMITED`) | Partially mitigated — in-memory, single-instance only; see R-3 |
| T11 | **Denial of service** | Flooding other write endpoints (payments, mortgages) with valid credentials | (1) Internet → App | **Not mitigated** — rate limiting is login-only today | Open — see R-3 |
| T12 | **Elevation of privilege** | A SUPPORT/RISK_ANALYST token used to call an ADMIN/UNDERWRITER-only endpoint | (1) Internet → App | `@PreAuthorize("hasAnyAuthority(...)")` per endpoint, enforced server-side (not client-side); tested for every role in `RbacTest` in both services | Mitigated |
| T13 | **Elevation of privilege** | Compromised LocalStack/AWS credentials used to publish a fabricated `LoanApproved` event | (3) App → Messaging | Same as T5 — no message signing yet | Open — see R-4 |

## Residual risk summary

The two genuinely open items are **T11** (no rate limiting beyond login) and **T5/T13** (no
message-level authenticity check on SNS/SQS events — anyone who can reach the queue can publish
a believable-looking event). Both are tracked in
[remediation-backlog.md](./remediation-backlog.md) as R-3 and R-4, neither rated **Critical**
(see [risk-register.md](./risk-register.md) R-3/R-4 for the likelihood/impact reasoning) — M6
sign-off only requires Critical items remediated, not every Medium/Low item closed.
