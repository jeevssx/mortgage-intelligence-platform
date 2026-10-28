# Remediation backlog (M6)

Prioritized by severity from [vulnerability-report.md](./vulnerability-report.md); same IDs as
[risk-register.md](./risk-register.md).

| ID | Severity | Finding | Status | Commit |
| --- | --- | --- | --- | --- |
| R-1 | High | `@PreAuthorize` denials returned 500 instead of 403 (V-1) | **Fixed** | `feature/M6-security-engineering` branch — `GlobalExceptionHandler` in both services (commits adding `feat(mortgage-service): JWT auth and RBAC` / `feat(servicing-service): validate mortgage-service's JWT, RBAC`) |
| R-2 | High | Hardcoded fallback JWT secret had no deployment guardrail (V-2) | **Fixed** | Same two commits above — `JwtService`/`JwtValidationService` constructors |
| R-3 | Medium | Rate limiting scoped to `POST /api/v1/auth/login` only; in-memory, single-instance (V-4) | Open | — (future milestone: extend to write endpoints, move to a shared store e.g. Redis if multi-instance) |
| R-4 | Medium | No message-level authenticity check on SNS/SQS lifecycle events (V-5) | Open | — (future milestone: sign/verify event payloads, or rely on stricter IAM scoping) |
| R-5 | Low | External IDs reflected verbatim in error messages (V-3) | Open | — (low priority: tighten path-variable validation before it reaches the error message) |
| R-6 | Critical (CVE rating) / High | Framework/third-party CVEs in the built image — Spring Framework, Spring Security, Tomcat, Netty (V-6) | **Partially fixed** | Same two commits above bump `spring-boot-starter-parent` 3.3.4 → 3.3.13 in both `pom.xml` files, closing `CVE-2024-38821`; remaining findings need a Spring Boot 4.x upgrade, tracked below |

## Why R-3/R-4/R-5/R-6 are not blockers

The M6 definition of done requires remediating **Critical findings that originate in this
project's own code or configuration** before sign-off. R-1 and R-2 are exactly that, and both
are fixed. R-6 carries a Critical CVE *rating* but is inherited from the current Spring Boot
3.3.x release line, not introduced by this project's code — see
[risk-register.md](./risk-register.md) R-6 and [vulnerability-report.md](./vulnerability-report.md)
V-6 for the full reasoning on why it's tracked (with the one patch-reachable CVE already fixed)
rather than attempted as a risky major-version migration under this milestone's time budget.
R-3, R-4, and R-5 are Medium/Low and documented with a clear owner and recommendation so they
aren't lost, but none of them block this milestone.

## Future milestone: Spring Boot 4.x upgrade (tracks the rest of R-6)

Not scheduled yet. When undertaken: bump `spring-boot-starter-parent` to the latest 4.x release,
re-run the full test suite (`mvn test` in both services — 29 + 14 tests today), re-verify the
JWT/RBAC flows live (same checks as `docs/security/security-controls.md`), and re-run this same
Trivy image scan to confirm the remaining findings clear.
