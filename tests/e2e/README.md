# E2E tests (M10)

Playwright + Cucumber, API-level — **there is no UI** in this capstone (every service is a JSON
API), so per the milestone spec's own guidance ("if no UI, use API-level Cucumber steps with
fetch/Playwright request context"), Playwright's `APIRequestContext` drives HTTP calls directly
instead of a browser. Page Object Model pattern is preserved as **API page objects**
(`page_objects/`): one class per resource area (`AuthApiPage`, `MortgageApiPage`,
`ServicingApiPage`, `AssistantApiPage`), each wrapping the request/response shape so step
definitions never build a request body or parse a response themselves.

## Run

Requires the real stack running — these are black-box HTTP tests, not mocks. Node 20, 22, or 24
(`@cucumber/cucumber` pinned to `^12.9.0` — v13 dropped Node 20 support and its bundled
`@cucumber/gherkin` is ESM-only, which fails with `ERR_REQUIRE_ESM` under cucumber-js's CJS
`require()`-based CLI on Node 20):

```bash
# from the repo root
docker compose up --build -d postgres db-init mortgage-service servicing-service ai-assistant

cd tests/e2e
npm ci
cp .env.example .env
npm test
```

## The five mandatory journeys

| Feature file | Journey | User stories |
| --- | --- | --- |
| `onboarding.feature` | J1 — Borrower → mortgage onboarding | `US-BOR-001`, `US-MTG-001` |
| `payment_and_servicing.feature` | J2 — Payment → servicing history visible | `US-PAY-001`, `US-SRV-001` |
| `delinquency.feature` | J3 — Delinquency state on a missed-payment mortgage | `US-DEL-001` |
| `authorization.feature` | J4 — Unauthorized/wrong-role access denied | `US-SEC-001` |
| `assistant.feature` | J5 — RAG question → grounded response with citation | `US-AI-001` |

## Known deviation from the original user story (documented, not silently patched)

`delinquency.feature`'s "current mortgage" scenario asserts `404 DELINQUENCY_NOT_FOUND` for
`MTG-1001`, not the `200` with `status: ACTIVE` that `US-DEL-001`'s acceptance criteria describes.
This is what `servicing-service` actually does (M4 implementation decision: no delinquency row
means no delinquency resource, a 404, rather than a 200 with empty/null fields) — the E2E test
asserts real behavior, not the aspirational M2-era story text. Tracked in
`docs/operations/known-issues.md`.

## Retry and reporting

`cucumber.js` sets `retry: 1` (one retry on failure, Session 34's flaky-test guidance) and tags
a scenario `@flaky` to opt it into that retry explicitly if a specific scenario needs it; nothing
is tagged `@flaky` today — all five journeys are deterministic against the seeded demo data
(`database/README.md`). `npm run report` publishes an HTML report
(`reports/cucumber-report.html`), uploaded as a CI artifact (`docs/operations/cicd.md`).

## Why these specific demo IDs

`MTG-1001` (ACTIVE), `MTG-1002` (DELINQUENT, 45 days past due), `BOR-001` — the same IDs every
other milestone's demo script uses (`database/README.md`), so these tests exercise exactly the
scenario the seed data was designed around. J1's borrower/mortgage creation uses randomly
generated IDs in the `MTG-9000..9899` / `BOR-9xx` range specifically to avoid colliding with the
seeded or other-milestone-reserved IDs.
