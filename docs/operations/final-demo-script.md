# Final demo script (M10, Session 36)

25 minutes of live system + 5 minutes Q&A, matching the Session 36 outline. This is a **solo
capstone build** — "assign demo roles per team member" (spec Task 10.5) collapses to one
presenter running every segment; the segment breakdown below is kept as written so the script
still reads correctly if this is ever run by a team.

**Setup, before the audience joins** (not part of the timed segments):

```bash
docker compose up --build -d postgres db-init mortgage-service servicing-service analytics-service ai-assistant
# Wait for all four to report healthy:
for i in $(seq 1 30); do
  curl -sf http://localhost:8080/actuator/health/readiness \
    && curl -sf http://localhost:8081/actuator/health/readiness \
    && curl -sf http://localhost:8000/health \
    && curl -sf http://localhost:8001/health && break
  sleep 3
done
```

Demo data: the seeded set (`database/README.md`) — `MTG-1001` (ACTIVE, current), `MTG-1002`
(DELINQUENT, 45 days past due), `BOR-001`. Don't run `tests/e2e` immediately before this demo
without resetting the DB afterward — its onboarding journey creates real rows
(`test-strategy.md`'s "Local test-isolation note").

---

## 1. Lifecycle — onboarding through payment (5 min)

Login as underwriter, create a borrower and a mortgage, then post a payment as the servicing
agent — the same three calls `tests/e2e/features/onboarding.feature` and
`payment_and_servicing.feature` automate.

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"underwriter@capstone.local","password":"Capstone#2026"}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['accessToken'])")

curl -s -X POST http://localhost:8080/api/v1/borrowers -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"borrowerExternalId":"BOR-900","firstName":"Demo","lastName":"Borrower","email":"demo@example.test"}'

curl -s -X POST http://localhost:8080/api/v1/mortgages -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mortgageExternalId":"MTG-9000","borrowerExternalId":"BOR-900","originalAmount":300000,"outstandingBalance":300000,"originationDate":"2026-01-01","loan":{"loanExternalId":"LOAN-9000","interestRate":0.0625,"termMonths":360,"underwritingDecision":"APPROVED"}}'
```

**Talking point**: underwriting decision lives on `loan`, not `mortgage` — the "underwriting
touchpoint" the spec calls out. Point at `US-MTG-001`/`US-BOR-001`
(`docs/requirements/user-stories.md`) as the traced requirement.

Then, as the servicing agent, post a payment on the real seeded mortgage:

```bash
SVC_TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"servicing@capstone.local","password":"Capstone#2026"}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['accessToken'])")

curl -s -X POST http://localhost:8080/api/v1/mortgages/MTG-1001/payments \
  -H "Authorization: Bearer $SVC_TOKEN" -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-payment-001" \
  -d '{"dueDate":"2026-04-01","paidDate":"2026-04-02","amount":1850.00,"status":"POSTED"}'

curl -s http://localhost:8081/api/v1/mortgages/MTG-1001/servicing-history \
  -H "Authorization: Bearer $SVC_TOKEN"
```

**Talking point**: the `PAYMENT_POSTED` event now in servicing history came through the real
SNS→SQS event path (M5), not a direct write — point at
`docs/architecture/event-catalog.md`/ADR-002.

## 2. Delinquency — missed payment path + analytics glance (5 min)

```bash
curl -s http://localhost:8081/api/v1/mortgages/MTG-1002/delinquency -H "Authorization: Bearer $SVC_TOKEN"
# {"mortgageExternalId":"MTG-1002","status":"DELINQUENT","delinquentSince":"2026-01-10","daysPastDue":45,"severity":"MODERATE"}

curl -s http://localhost:8000/api/v1/analytics/portfolio-summary
# {"totalMortgages":12,"activeMortgages":6,"delinquentMortgages":3,"pendingMortgages":1,
#  "closedMortgages":2,"outstandingBalanceTotal":2707750.0,"delinquentBalanceTotal":799250.0,
#  "delinquencyRate":0.3333,"asOf":"<now>"}
```

**Talking point**: the 30-day rule (`US-DEL-002`) and the `LoanDelinquent` event (`US-DEL-003`)
are what populated this row — not a manual edit. Glance at
`monitoring/splunk/dashboard.json`/`alert-payment-latency.json` here (never fired against a live
Splunk instance in this build — say so plainly, point at `slo.md`'s own caveat, don't claim
otherwise).

## 3. Security — RBAC deny (3 min)

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/api/v1/mortgages/MTG-1001
# 401 — no token at all

SUPPORT_TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"support@capstone.local","password":"Capstone#2026"}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['accessToken'])")

curl -s -X POST http://localhost:8080/api/v1/mortgages/MTG-1001/payments \
  -H "Authorization: Bearer $SUPPORT_TOKEN" -H "Content-Type: application/json" \
  -d '{"dueDate":"2026-04-01","amount":100,"status":"POSTED"}'
# {"code":"FORBIDDEN","message":"Role does not permit this operation", ...} — 403
```

**Talking point**: this exact sequence is `tests/e2e/features/authorization.feature` (J4,
`US-SEC-001`) — not a one-off demo trick, a regression-tested contract that runs on every PR.

## 4. AI — RAG with citation (3 min)

```bash
curl -s -X POST http://localhost:8001/api/v1/assistant/ask \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"What is the maximum debt-to-income ratio?"}'
# {"answer":"...", "citations":[{"documentId":"...","section":"...","chunkId":"..."}],
#  "confidence":0.25+, "requiresHumanApproval":false}

curl -s -X POST http://localhost:8001/api/v1/assistant/ask \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"What is the weather forecast for tomorrow?"}'
# {"answer":"I don't have enough information...", "citations":[], "requiresHumanApproval":true}
```

**Talking point**: no LLM API key in this build — retrieval is TF-IDF, generation is extractive
(`ai/mortgage-knowledge-assistant/README.md`). The point being demonstrated is the **grounding
contract** (always cite, degrade to "insufficient context" rather than guess, flag
decision-adjacent questions for human approval), which holds regardless of which embedding/LLM
backend is plugged in — say this explicitly rather than implying a production LLM is live.

## 5. Ops — CI/CD, Terraform, runbook/RCA (4 min)

- Walk `.gitlab-ci.yml`'s 9 stages out loud (`docs/operations/cicd.md`'s table) — point out which
  are hard gates (SAST, secrets, E2E) vs. report-only (SCA/container scan) and *why*
  (`cicd.md`'s "Why SCA/Container Scan are report-only" section — the reasoning, not just the
  policy).
- `cd infrastructure/terraform/environments/dev && terraform plan` — show it plans clean against
  LocalStack; mention `prod`/`test` use a real-AWS S3+DynamoDB backend, never applied (no AWS
  account — `infrastructure/terraform/README.md`).
- Point at [rca-2026-10-28.md](./rca-2026-10-28.md) — a real incident (the actuator health-probe
  path bug) found, triaged, and fixed with a timestamped RCA, not a synthetic example.

## 6. Q&A — architecture and one ADR decision (5 min)

Have ready: `docs/adr/ADR-002-microservice-decomposition.md` (why mortgage-service and
servicing-service are separate, and why servicing-service's "fast lookup" is DynamoDB rather than
querying mortgage-service's Postgres directly) as the one ADR decision to walk through if asked.
`docs/adr/ADR-001-service-data-ownership.md` and `ADR-003-kinesis-vs-sqs-only.md` as backups for
likely follow-up questions.

---

## Rehearsal checklist (record actual timestamps here before the real demo)

Every command in segments 1-5 was run live against the real stack on 2026-11-04 to confirm it
produces exactly the output shown in this script (not just written and assumed to work) — this
is a **command-correctness rehearsal**, not a timed spoken walkthrough, which needs an actual
presenter talking through the talking points out loud. Do that pass before the real demo and
fill in the table below.

| Segment | Target | Commands verified live (2026-11-04) | Rehearsal 1 (spoken, actual) | Notes |
| --- | --- | --- | --- | --- |
| 1. Lifecycle | 5 min | Yes — borrower/mortgage create, payment post, servicing history all returned the documented shape | | |
| 2. Delinquency | 5 min | Yes — delinquency + portfolio-summary outputs match exactly | | |
| 3. Security | 3 min | Yes — 401 then 403/FORBIDDEN reproduced | | |
| 4. AI | 3 min | Yes — grounded answer (confidence 0.2506, 1 citation) and insufficient-context (0 citations, human approval true) both reproduced | | |
| 5. Ops | 4 min | `terraform plan` reproduced (30 to add, clean) — CI/RCA walkthrough is narration only, nothing to execute | | |
| 6. Q&A | 5 min | n/a — no commands | | |
| **Total** | **25 min** | | | |

After rehearsing: reset the dev DB (`database/scripts/reset-dev-db.sh`) before the real demo if
rehearsal created `MTG-9000`/`BOR-900` or posted extra payments, so the real run starts from the
same clean seed state documented above.
