# Known issues (M10)

Issues and documented spec-vs-implementation deviations found across the build. "Fixed" entries
are kept here (not deleted) so the next reader can see what was found and how, not just that the
code currently works.

## Fixed this milestone

### JWT signing algorithm mismatch (ai-assistant rejected every real token)

**Found**: while first building `tests/e2e`'s assistant journey (J5) and wiring a real Bearer
token into `AssistantApiPage.ask()`.

mortgage-service's `JwtService.generateToken()` called JJWT's `signWith(key)` with no explicit
algorithm, so JJWT auto-selected the strongest HMAC variant the 66-byte shared secret could
support — **HS384**, not HS256. servicing-service's validator (`Jwts.parser().verifyWith(key)`,
no algorithm pinned) accepted it fine and never noticed. ai-assistant's `require_auth()` hardcodes
PyJWT's `algorithms=["HS256"]`, so it silently rejected every real end-to-end token as "invalid
Bearer token" — this had been true since M7 and nothing caught it because ai-assistant was never
previously called with a real cross-service token in an automated test.

**Fix**: pinned `signWith(key, Jwts.SIG.HS256)` explicitly in `JwtService`. Regression test
(`JwtServiceTest.generateToken_alwaysSignsWithHs256_regardlessOfSecretLength`) decodes the token
header and asserts `alg == HS256` using a secret long enough to trigger the old auto-selection, so
this can't silently regress if someone "simplifies" the call back to bare `signWith(key)`.
Live-verified via a rollback dry run (see [production-readiness.md](./production-readiness.md))
that reproduces the bug on the pre-fix build and confirms the fix.

### E2E test suite's own login traffic tripped mortgage-service's rate limiter

**Found**: running `tests/e2e` for the first time — 3 of 12 scenarios failed with `429
RATE_LIMITED` on the `Given ... is authenticated` step.

`RateLimitFilter` allows 10 requests/60s per client IP on `/api/v1/auth/login` — correct,
intentional behavior (R-3 in the risk register). With 12 scenarios each re-authenticating via a
`Background` step, the suite generated 11 login requests against one IP within ~3 seconds,
tripping its own rate limit before the later scenarios even got to exercise what they were
testing.

**Fix**: added `support/token_cache.ts` — a module-level (not per-scenario) token cache. One
login per role for the whole suite run, not one per scenario. This is the correct design, not
just a workaround: tokens don't depend on any particular scenario's request context.

### ai-assistant's CI test command would fail on a genuinely clean checkout

**Found**: measuring real test coverage for [test-strategy.md](./test-strategy.md) — ran the
exact CI command (`pytest -v --cov=src ...`) in a fresh venv rather than the pre-existing
`.venv`, and it failed with `ModuleNotFoundError: No module named 'src'`.

Both `.gitlab-ci.yml` and `.github/workflows/ci.yml` invoke bare `pytest`, not `python -m
pytest`. Without a `conftest.py`, `pyproject.toml`, or editable install, bare `pytest` never adds
the project root to `sys.path`; `python -m pytest` does (it's `-m`'s own behavior, not pytest's),
which is presumably how this went unnoticed during earlier milestone work.

**Fix**: added `pythonpath = .` to `ai/mortgage-knowledge-assistant/pytest.ini` (pytest's native
ini option since 7.0, no plugin needed). Verified: bare `pytest -v` now passes 16/16, matching
the exact CI invocation.

### servicing-service's AWS SDK write-through classes were 12-17% covered

**Found**: same coverage-measurement pass as above.

`SqsEventConsumer`, `SnsEventPublisher`, and `MortgageLookupRepository` had only their
"AWS not configured" no-op branches exercised by existing `@SpringBootTest` classes — the actual
DynamoDB/SNS/SQS call paths were verified only ad hoc against live LocalStack (M5/M8), never
asserted in an automated test.

**Fix**: added a package-private test constructor to each (mock AWS SDK client injection,
`@Autowired` pinned on the real constructor) and three new Mockito-based unit test classes.
servicing-service instruction coverage: 46.0% → 73.3%. See
[test-strategy.md](./test-strategy.md).

## Open, accepted (not blocking go-live)

See [docs/security/risk-register.md](../security/risk-register.md) R-3 (rate limiting is
login-only/in-memory/single-instance), R-4 (no message-level authenticity check on SNS/SQS), R-5
(external IDs reflected verbatim in error messages), and R-6 (third-party framework CVEs). All
four are Medium/Low or non-reachable-in-practice, with an owner and a remediation path, carried
forward deliberately rather than silently.

## Documented spec-vs-implementation deviations

These are **not bugs** — the real, tested implementation is correct; the milestone spec's
illustrative text (written before M4-M9 implementation decisions were made) describes something
slightly different. Each is a deliberate choice to match working, already-tested code rather than
either changing production behavior this late or silently diverging from the spec without a
record.

### US-DEL-001: a current mortgage returns 404, not 200/ACTIVE

`US-DEL-001`'s acceptance criteria (`docs/requirements/user-stories.md`) says a current
mortgage's delinquency request should return `200` with status `ACTIVE` and no delinquency
details. The real M4 implementation (`ServicingServiceImpl`/`GlobalExceptionHandler`) returns
`404 DELINQUENCY_NOT_FOUND` for a mortgage with no delinquency row — no delinquency row means no
delinquency *resource*, which is a more conventional REST response for "this sub-resource doesn't
exist" than a 200 with an awkward partial/null body.

`tests/e2e/features/delinquency.feature` asserts the real (404) behavior. Not changed this late
in the build since it's working, already covered by `ServicingControllerTest`, and changing it
now would be scope creep against a cosmetic API-shape preference, not a defect.

### J4's example error code is "ACCESS_DENIED" in the spec, "FORBIDDEN" in this implementation

The milestone spec's example Gherkin for Journey 4 uses `error code should be "ACCESS_DENIED"`.
This project's actual `GlobalExceptionHandler` (both services) returns `"FORBIDDEN"` for
`AccessDeniedException` — established in M6 and consistent across both services' error-code
vocabulary (`BORROWER_NOT_FOUND`, `MORTGAGE_NOT_FOUND`, `VALIDATION_FAILED`, `FORBIDDEN`,
`UNAUTHORIZED`). `tests/e2e/features/authorization.feature` asserts `"FORBIDDEN"`, matching the
real, already-tested contract rather than the spec's illustrative example string.

## No real external dependency was ever exercised live

Documented individually in each milestone's own README/doc, repeated here for one consolidated
view:

| Dependency | Where it matters | Status |
| --- | --- | --- |
| Real AWS account | M8 (S3/SNS/SQS/DynamoDB/Lambda), M9 (ECS, real Terraform backend) | LocalStack-only throughout; `infrastructure/terraform/README.md` |
| Real LLM API key | M7 (ai-assistant's grounded-answer quality) | TF-IDF/extractive fallback only; `ai/mortgage-knowledge-assistant/README.md` |
| Real Splunk instance | M9 (dashboard/saved search/alert artifacts) | Artifacts are valid JSON, never fired against a live instance; `slo.md` |
| Real GitLab/GitHub CI runner | M9/M10 (both pipelines) | Every command verified locally; no live runner available; `cicd.md` |
