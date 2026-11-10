# Risk register (M6)

Cross-references: [vulnerability-report.md](./vulnerability-report.md) (V-#),
[remediation-backlog.md](./remediation-backlog.md) (same R-# IDs).

| ID | Risk | Likelihood | Impact | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| R-1 | `@PreAuthorize` denials returned 500 instead of 403 (V-1) | High (hit on first RBAC test run) | Medium (confusing signal, not an actual bypass) | mortgage-service / servicing-service maintainer | **Closed** — fixed this milestone, verified by `RbacTest` in both services |
| R-2 | Hardcoded fallback JWT secret with no deployment guardrail (V-2) | Low (requires forgetting to set a documented env var) | Critical (full auth/RBAC bypass if it happens) | mortgage-service / servicing-service maintainer | **Closed** — fail-fast outside dev/test profiles, verified by `JwtServiceTest` / `JwtValidationServiceTest` |
| R-3 | Rate limiting scoped to login only; in-memory, single-instance (V-4) | Medium (any sensitive write endpoint can be flooded today) | Medium (availability/brute-force on business operations, not data exposure) | mortgage-service maintainer | Open — tracked in remediation backlog, no committed date |
| R-4 | No message-level authenticity check on SNS/SQS lifecycle events (V-5) | Low (requires access to the queue itself, which already has a network/IAM boundary) | Medium (a forged event could create a misleading `event_inbox` entry) | servicing-service maintainer | Open — deferred to a future milestone, not in M6 scope |
| R-5 | External IDs reflected verbatim in error messages (V-3) | Low (requires a future browser-rendered consumer of this API) | Low (no XSS vector in the current architecture) | mortgage-service maintainer | Open — cosmetic/defense-in-depth, not blocking |
| R-6 | Framework/third-party CVEs in the built image: 9 Critical, 43 High, mostly requiring a Spring Boot 4.x major upgrade to fully close (V-6) | Low (exploiting most of these requires a feature this app doesn't use, e.g. XSLT views) | Critical by CVE rating, but mitigated in practice by non-reachability (see V-6) | Platform maintainer (future migration milestone) | Partially closed — the one patch-level-fixable CVE (`CVE-2024-38821`) was fixed by the 3.3.4→3.3.13 bump this milestone; the rest are open, tracked for a dedicated Spring Boot 4.x upgrade |

## Sign-off

Per the M6 definition of done ("Remediate all Critical findings before M6 sign-off"): **every
Critical/High finding that originates in this project's own code was remediated** (R-1, R-2).
R-6 carries a Critical CVE *rating* but is a third-party framework dependency issue inherited
from the current Spring Boot 3.3.x release line, not a defect introduced by this project —
Trivy's library-presence scanning doesn't assess whether this codebase's usage actually reaches
the vulnerable code path (several don't, e.g. the `spring-webmvc` RCE requires `XsltView`, which
neither service uses). It's tracked with an owner and a concrete remediation path (major
framework upgrade) rather than silently ignored, which is what this register is for. R-3, R-4,
and R-5 are Medium/Low and explicitly acceptable to carry forward per the remediation backlog.
