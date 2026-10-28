# Security controls (M6)

Covers authentication, RBAC, data classification, and encryption for `mortgage-service` and
`servicing-service`. Roles and seed users: [standards.md](https://github.com/UID-Technologies/capstone-secondary-mortgage-intelligence-platform/blob/main/guides/standards.md#security-roles-m6).

## Authentication

- `POST /api/v1/auth/login` on `mortgage-service` (8080) checks `username`/BCrypt(`password`)
  against `app_user`, then issues an HS256 JWT: `{ sub, iss, roles: [role], iat, exp }`.
- Token TTL: 3600s (`JWT_EXPIRY_SECONDS`). `servicing-service` validates the **same** token with
  the **same** `JWT_SECRET** — no inter-service call is needed to verify a token (see
  [ADR-002](../adr/ADR-002-microservice-decomposition.md)). Both services must be configured with
  an identical `JWT_SECRET` or cross-service calls will all 401.
- Password hashes: BCrypt (`org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder`).
  Plaintext passwords and tokens are never logged (`AuthServiceImpl` logs only `LOGIN_SUCCESS`/
  `LOGIN_FAILED` with the username on success, nothing on failure).
- **Dev-only default secret.** If `JWT_SECRET` is unset, both services fall back to the same
  hardcoded, clearly-named `insecure-dev-only-...` string (logged as a `WARN` on startup) so
  local dev doesn't require extra setup. **Never use this outside local development** — set
  `JWT_SECRET` to a random 32+ byte value in any shared or deployed environment.

## RBAC matrix

| Endpoint | ADMIN | UNDERWRITER | SERVICING_AGENT | RISK_ANALYST | SUPPORT |
| --- | --- | --- | --- | --- | --- |
| `POST /api/v1/borrowers` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `GET /api/v1/borrowers/{id}` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /api/v1/mortgages` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `GET /api/v1/mortgages/{id}`, `GET /api/v1/mortgages` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /api/v1/mortgages/{id}/payments` | ✓ | ✗ | ✓ | ✗ | ✗ |
| `GET /api/v1/mortgages/{id}/payments` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET .../servicing-history`, `GET .../delinquency` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST .../servicing-events` | ✓ | ✗ | ✓ | ✗ | ✗ |
| `POST /api/v1/auth/login` | public (no auth required) | | | | |
| `GET /actuator/health` | public (no auth required) | | | | |

Enforced with Spring Security `@PreAuthorize("hasAnyAuthority(...)")` on each restricted
controller method, on top of a filter-chain-level `anyRequest().authenticated()` default (so a
new endpoint is unauthenticated-closed by default, not open, if someone forgets the annotation).
Tested in `RbacTest` in both services (wrong role → 403, right role → 2xx, no token → 401).

## Data classification (borrower fields)

| Field | Classification | Notes |
| --- | --- | --- |
| `borrower_external_id` | Internal | Business identifier, not secret, but not public |
| `first_name`, `last_name` | Confidential | PII |
| `email`, `phone` | Confidential | PII, contact channel |
| `date_of_birth` | Restricted | PII usable for identity verification/fraud |
| `mortgage_external_id`, `status`, balances | Internal | Business data, not PII on its own |
| `password_hash` | Restricted | Never returned by any API, never logged |
| JWT (`accessToken`) | Restricted | Bearer credential; never logged, never persisted server-side |

## Encryption

- **In transit:** local dev runs plain HTTP (documented limitation — see "Implementation
  requirements" in [m06-security-engineering.md](https://github.com/UID-Technologies/capstone-secondary-mortgage-intelligence-platform/blob/main/milestones/m06-security-engineering.md)).
  Any shared/deployed environment must terminate TLS at the ingress (see
  `docs/architecture/deployment-architecture.md`), not inside the Java services.
- **At rest:** no encryption is implemented in this capstone build (PostgreSQL/LocalStack are
  local containers). A real AWS deployment plan: RDS encryption-at-rest (KMS-managed key) for
  `mortgage_intel`, S3 default encryption (SSE-S3 or SSE-KMS) for the documents bucket. Out of
  scope to implement here per M6/M8 scope.

## OWASP / API hardening applied

- **Validation:** Bean Validation (`@Valid`) on every `POST` body (M4 already had this; unchanged).
- **Headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Content-Security-Policy: default-src 'none'`, `Referrer-Policy: no-referrer`,
  `Cache-Control: no-store` on every response (`SecurityHeadersFilter` in both services).
- **Rate limiting:** `POST /api/v1/auth/login` only — 10 requests/60s per client IP
  (`RateLimitFilter`, in-memory sliding log). **Known limitation:** in-memory means it resets on
  restart and doesn't coordinate across multiple instances; a real multi-replica deployment needs
  a shared store (e.g. Redis). Not applied to other endpoints — see
  [remediation-backlog.md](./remediation-backlog.md) R-3.
- **Injection defense:** 100% JPA/parameterized queries, no string-concatenated SQL anywhere in
  either service. Verified live: a `' OR '1'='1` payload in a mortgage ID path segment returns a
  clean `404 MORTGAGE_NOT_FOUND` (the literal string, not SQL), never a 500 or a DB error leak.
- **CSRF:** disabled — justified because both APIs are stateless bearer-token APIs with no
  session cookie, so there is no ambient browser credential for a forged cross-site request to
  ride on (OWASP's CSRF guidance treats this as a session/cookie-specific attack).

## Known gaps (tracked, not blocking)

See [remediation-backlog.md](./remediation-backlog.md) for the full list with severity and
owner — notably: no CORS policy defined yet (irrelevant until a browser-based frontend exists),
rate limiting scoped to login only, and the dev-only JWT secret fallback.
