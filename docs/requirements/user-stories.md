# User Stories

Stories are grouped by the epics in [backlog-epics.md](./backlog-epics.md) (names used verbatim). Personas come from [personas.md](./personas.md). Story IDs are stable: a story is never renumbered or reused; replaced stories get a new ID.

**Priority:** P1 = must for its target milestone, P2 = should, P3 = could.
**Sprint:** see [sprint-plans.md](./sprint-plans.md).

Summary: **31 stories** across 11 epics.

---

## Borrower Management

### US-BOR-001 — Create borrower
**Persona:** Servicing Agent · **Priority:** P1 · **Milestone:** M4

As a servicing agent,
I want to create a borrower record with contact details,
so that mortgages can be linked to a known party.

**Acceptance criteria**
- Given a valid request with a unique `borrowerExternalId` (`BOR-###`), first name, last name, and email
  When I submit `POST /api/v1/borrowers`
  Then the system returns `201` with the borrower's ID and the data I sent.
- Given a `borrowerExternalId` that already exists
  When I submit the request
  Then the system returns `409` with the standard error envelope.
- Given a missing email or a malformed `borrowerExternalId`
  When I submit the request
  Then the system returns `400` with code `VALIDATION_ERROR`.

### US-BOR-002 — Get borrower
**Persona:** Servicing Agent · **Priority:** P1 · **Milestone:** M4

As a servicing agent,
I want to retrieve a borrower by business ID,
so that I can confirm who I am speaking with.

**Acceptance criteria**
- Given borrower `BOR-001` exists
  When I request `GET /api/v1/borrowers/BOR-001`
  Then the system returns `200` with name, email, and phone.
- Given `BOR-999` does not exist
  When I request it
  Then the system returns `404` with code `BORROWER_NOT_FOUND`.

### US-BOR-003 — List a borrower's mortgages
**Persona:** Risk Analyst · **Priority:** P2 · **Milestone:** M4

As a risk analyst,
I want to see all mortgages held by one borrower,
so that I can assess total exposure to that borrower.

**Acceptance criteria**
- Given `BOR-001` holds `MTG-1001` and `MTG-1003`
  When I request the borrower's mortgages
  Then both are returned with status and outstanding balance.

---

## Mortgage Management

### US-MTG-001 — Create mortgage
**Persona:** Underwriter · **Priority:** P1 · **Milestone:** M4

As an underwriter,
I want to create a mortgage linked to an existing borrower,
so that the loan can move through underwriting and servicing.

**Acceptance criteria**
- Given borrower `BOR-001` exists and `MTG-1010` does not
  When I submit `POST /api/v1/mortgages` with amount, origination date, and loan terms
  Then the system returns `201`, the mortgage status is `PENDING`, and a `MortgageCreated` event is published (M5).
- Given the borrower does not exist
  When I submit the request
  Then the system returns `404` and nothing is created.
- Given `outstandingBalance` is negative or greater than `originalAmount`
  When I submit the request
  Then the system returns `400`.

### US-MTG-002 — Get mortgage
**Persona:** Servicing Agent · **Priority:** P1 · **Milestone:** M4

As a servicing agent,
I want to retrieve a mortgage by `MTG-####`,
so that I can see its status, balance, and loan terms.

**Acceptance criteria**
- Given `MTG-1001` exists
  When I request `GET /api/v1/mortgages/MTG-1001`
  Then the system returns `200` with status `ACTIVE`, outstanding balance, and linked loan `LOAN-2001`.
- Given `MTG-9999` does not exist
  When I request it
  Then the system returns `404` with code `MORTGAGE_NOT_FOUND`.

### US-MTG-003 — Search mortgages by status
**Persona:** Servicing Agent · **Priority:** P2 · **Milestone:** M4

As a servicing agent,
I want to filter mortgages by status,
so that I can work my queue of delinquent or pending loans.

**Acceptance criteria**
- Given seeded data
  When I request mortgages with `status=DELINQUENT`
  Then only `MTG-1002`, `MTG-1005`, and `MTG-1008` are returned.
- Given an invalid status value
  When I request it
  Then the system returns `400`.

---

## Underwriting

### US-UW-001 — Record underwriting decision
**Persona:** Underwriter · **Priority:** P1 · **Milestone:** M4

As an underwriter,
I want to approve or decline a pending loan,
so that the decision is recorded and the mortgage moves to the right status.

**Acceptance criteria**
- Given `LOAN-2009` is `PENDING`
  When I approve it
  Then `underwriting_decision` becomes `APPROVED`, the mortgage becomes `ACTIVE`, and a `LoanApproved` event is published (M5).
- Given a loan is declined
  When I submit the decision
  Then the mortgage becomes `CLOSED` and a servicing history entry `UNDERWRITING_DECLINED` is recorded.
- Given a loan that is already decided
  When I submit another decision
  Then the system returns `409`.

### US-UW-002 — View loan terms
**Persona:** Underwriter · **Priority:** P2 · **Milestone:** M4

As an underwriter,
I want to see a loan's rate, term, and decision alongside the mortgage,
so that I can review it without switching systems.

**Acceptance criteria**
- Given `LOAN-2001` is linked to `MTG-1001`
  When I retrieve `MTG-1001`
  Then the response includes interest rate `0.0625`, term `360`, and decision `APPROVED`.

---

## Servicing

### US-SRV-001 — Retrieve servicing history
**Persona:** Servicing Agent · **Priority:** P1 · **Milestone:** M4

As a servicing agent,
I want to retrieve mortgage servicing history
so that I can understand the current status of a loan.

**Acceptance criteria**
- Given a valid mortgage ID
  When servicing history is requested
  Then the system returns servicing events in chronological order.
- Given an unknown mortgage ID
  When servicing history is requested
  Then the system returns `404` with code `MORTGAGE_NOT_FOUND`.

### US-SRV-002 — Record a servicing event
**Persona:** Servicing Agent · **Priority:** P2 · **Milestone:** M4

As a servicing agent,
I want to log a borrower contact on a mortgage,
so that the next agent knows what was discussed.

**Acceptance criteria**
- Given `MTG-1002` exists
  When I post an event of type `BORROWER_CONTACT` with a description
  Then it appears at the end of the servicing history with the current timestamp.
- Given an empty description
  When I post the event
  Then the system returns `400`.

### US-SRV-003 — Servicing history from lifecycle events
**Persona:** Support Engineer · **Priority:** P2 · **Milestone:** M5

As a support engineer,
I want lifecycle events to create servicing history entries automatically,
so that history is complete without manual entry.

**Acceptance criteria**
- Given a `PaymentReceived` event for `MTG-1001`
  When the servicing service consumes it
  Then a `PAYMENT_POSTED` entry with the event's correlation ID in logs is recorded.
- Given the same event is delivered twice
  When it is consumed
  Then only one history entry exists.

---

## Payment

### US-PAY-001 — Post payment
**Persona:** Servicing Agent · **Priority:** P1 · **Milestone:** M4

As a servicing agent,
I want to post a borrower payment against a mortgage,
so that the outstanding balance and payment history are accurate.

**Acceptance criteria**
- Given `MTG-1001` is `ACTIVE`
  When I post a payment with due date, paid date, amount, and status `POSTED`
  Then the system returns `201`, the outstanding balance is reduced in the same transaction, and a `PaymentReceived` event is published (M5).
- Given a request with the same `Idempotency-Key` as a previous request
  When I post it again
  Then no duplicate payment is created and the original result is returned (or `409` per API design).
- Given status `POSTED` without a paid date, or a non-positive amount
  When I post it
  Then the system returns `400`.

### US-PAY-002 — List payments
**Persona:** Servicing Agent · **Priority:** P1 · **Milestone:** M4

As a servicing agent,
I want to list payments for a mortgage,
so that I can answer borrower questions about what was received.

**Acceptance criteria**
- Given `MTG-1002` has 6 payment rows
  When I request its payments
  Then all 6 are returned ordered by due date, including the 2 unpaid `SCHEDULED` installments.

### US-PAY-003 — Handle failed and reversed payments
**Persona:** Servicing Agent · **Priority:** P2 · **Milestone:** M4

As a servicing agent,
I want failed and reversed payments recorded distinctly,
so that the installment is not treated as paid.

**Acceptance criteria**
- Given a payment is reversed
  When the reversal is recorded
  Then the payment status is `REVERSED`, the balance is restored, and the installment counts as unpaid for delinquency.

---

## Delinquency

### US-DEL-001 — Get delinquency status
**Persona:** Servicing Agent · **Priority:** P1 · **Milestone:** M4

As a servicing agent,
I want to see a mortgage's delinquency status,
so that I can prioritize collection outreach.

**Acceptance criteria**
- Given `MTG-1002` is delinquent
  When I request `GET /api/v1/mortgages/MTG-1002/delinquency`
  Then the system returns status `DELINQUENT`, `delinquentSince` `2026-01-10`, `daysPastDue` `45`, severity `MODERATE`.
- Given `MTG-1001` is current
  When I request its delinquency
  Then the system returns status `ACTIVE` with no delinquency details.

### US-DEL-002 — Apply the 30-day delinquency rule
**Persona:** Risk Analyst · **Priority:** P1 · **Milestone:** M4

As a risk analyst,
I want mortgages marked delinquent automatically when an installment is 30+ days unpaid,
so that delinquency reporting is consistent.

**Acceptance criteria**
- Given an installment is unpaid 30 or more days after its due date
  When the delinquency batch runs
  Then the mortgage status becomes `DELINQUENT` and a delinquency row is created with days past due and severity.
- Given an installment is 23 days past due (`MTG-1004` in seed)
  When the batch runs
  Then the mortgage remains `ACTIVE`.

### US-DEL-003 — Delinquency events
**Persona:** Support Engineer · **Priority:** P2 · **Milestone:** M5

As a support engineer,
I want `PaymentMissed` and `LoanDelinquent` events emitted,
so that downstream systems react without polling.

**Acceptance criteria**
- Given a mortgage becomes delinquent
  When the status changes
  Then a `LoanDelinquent` event with `daysPastDue` and `severity` is published with the correlation ID.

---

## Analytics

### US-ANL-001 — Portfolio summary
**Persona:** Risk Analyst · **Priority:** P1 · **Milestone:** M3

As a risk analyst,
I want a portfolio summary of counts, balance, and delinquency rate,
so that I can report portfolio health.

**Acceptance criteria**
- Given the seed data
  When I request `GET /api/v1/analytics/portfolio-summary`
  Then `totalMortgages` = 12, `delinquentMortgages` = 3, and `delinquencyRate` = DELINQUENT / (ACTIVE + DELINQUENT) = 0.3333.
- Given any data
  When I compare the response to SQL aggregates
  Then counts match exactly and balances match to the cent.

### US-ANL-002 — Delinquency report
**Persona:** Risk Analyst · **Priority:** P1 · **Milestone:** M3

As a risk analyst,
I want a list of delinquent mortgages with days past due and severity,
so that I can see which loans need attention first.

**Acceptance criteria**
- Given the seed data
  When I request `GET /api/v1/analytics/delinquency`
  Then `MTG-1002`, `MTG-1005`, and `MTG-1008` are returned, sorted by days past due descending.

### US-ANL-003 — Borrower risk summary
**Persona:** Risk Analyst · **Priority:** P1 · **Milestone:** M3

As a risk analyst,
I want a risk summary for one borrower,
so that I can see their total balance and delinquent loans.

**Acceptance criteria**
- Given `BOR-002` has one delinquent and one pending mortgage
  When I request `GET /api/v1/analytics/borrowers/BOR-002/risk-summary`
  Then the response shows 2 mortgages, outstanding total 574000.00, and 1 delinquent mortgage.
- Given an unknown borrower
  When I request it
  Then the system returns `404`.

### US-ANL-004 — Payment trends
**Persona:** Risk Analyst · **Priority:** P2 · **Milestone:** M3

As a risk analyst,
I want monthly posted payment totals and on-time rates,
so that I can spot deteriorating payment behavior.

**Acceptance criteria**
- Given a date range
  When I request `GET /api/v1/analytics/payment-trends?from=...&to=...`
  Then one bucket per month is returned with `postedAmount` and `onTimeRate`.
- Given `from` is after `to`
  When I request it
  Then the system returns `400`.

---

## Document Management

### US-DOC-001 — Upload mortgage document
**Persona:** Underwriter · **Priority:** P1 · **Milestone:** M3

As an underwriter,
I want to upload a document to a mortgage,
so that the loan file is complete and retrievable.

**Acceptance criteria**
- Given `MTG-1001` exists
  When I upload a PDF with document type `INCOME_VERIFICATION`
  Then it is stored at `mortgages/MTG-1001/{uuid}-{fileName}` in S3, a `document` row is created, and the response includes `documentId`, `s3Key`, and `correlationId`.
- Given S3 is unavailable
  When I upload
  Then the system returns `502` and no `document` row is created.

### US-DOC-002 — List mortgage documents
**Persona:** Servicing Agent · **Priority:** P2 · **Milestone:** M4

As a servicing agent,
I want to list documents attached to a mortgage,
so that I can find the right file during a borrower call.

**Acceptance criteria**
- Given `MTG-1001` has 2 documents
  When I list its documents
  Then both are returned with type, file name, and upload time.

---

## Security

### US-SEC-001 — Deny unauthorized access
**Persona:** Security Analyst · **Priority:** P1 · **Milestone:** M6

As a security analyst,
I want requests without a valid token rejected,
so that borrower data is only visible to authenticated users.

**Acceptance criteria**
- Given no `Authorization` header
  When any `/api/v1` endpoint is called
  Then the system returns `401` with the standard error envelope.
- Given a valid `SUPPORT` token
  When `POST /api/v1/mortgages/{id}/payments` is called
  Then the system returns `403`.

### US-SEC-002 — Block secrets in the repository
**Persona:** Security Analyst · **Priority:** P1 · **Milestone:** M2

As a security analyst,
I want every pull request scanned for secrets,
so that credentials never reach the shared repository.

**Acceptance criteria**
- Given a PR adds a string matching a known secret pattern
  When CI runs
  Then the secret-scan job fails and the PR cannot be merged.

### US-SEC-003 — Role management
**Persona:** Administrator · **Priority:** P2 · **Milestone:** M6

As an administrator,
I want to assign roles to users,
so that each persona has only the access they need.

**Acceptance criteria**
- Given user `risk@capstone.local`
  When I assign `RISK_ANALYST`
  Then the user can read analytics but receives `403` on payment posting.

---

## AI Assistant

### US-AI-001 — Grounded policy Q&A
**Persona:** Underwriter · **Priority:** P1 · **Milestone:** M7

As an underwriter,
I want to ask policy questions and get answers grounded in approved documents,
so that I can make consistent decisions quickly.

**Acceptance criteria**
- Given the policy corpus is indexed
  When I ask "What is the maximum debt-to-income ratio?"
  Then the answer cites at least one source document and passage.
- Given a question outside the corpus
  When I ask it
  Then the assistant says it cannot answer from approved sources instead of guessing.

### US-AI-002 — Servicing procedure Q&A
**Persona:** Servicing Agent · **Priority:** P2 · **Milestone:** M7

As a servicing agent,
I want to ask how to handle a delinquent borrower,
so that I follow the approved procedure.

**Acceptance criteria**
- Given a question about delinquency outreach
  When I ask it
  Then the answer includes the procedure steps and their source.

---

## Operations

### US-OPS-001 — Health endpoints
**Persona:** Support Engineer · **Priority:** P1 · **Milestone:** M3

As a support engineer,
I want every service to expose a health endpoint,
so that load balancers and monitors can detect failures.

**Acceptance criteria**
- Given the analytics service is running
  When I call `GET /health`
  Then it returns `200` with `{"status":"UP","service":"mortgage-analytics-service"}`.

### US-OPS-002 — Correlated structured logs
**Persona:** Support Engineer · **Priority:** P1 · **Milestone:** M3

As a support engineer,
I want every log line to include the request's correlation ID,
so that I can trace one request across services.

**Acceptance criteria**
- Given a request with header `X-Correlation-Id: demo-m3-001`
  When it is processed
  Then every log line for that request is JSON containing `"correlationId": "demo-m3-001"`, and the response echoes the header.
- Given no header
  When a request is processed
  Then a UUID is generated and used the same way.

### US-OPS-003 — CI pipeline gates
**Persona:** Support Engineer · **Priority:** P2 · **Milestone:** M2, M9

As a support engineer,
I want CI to validate migrations and run tests on every PR,
so that broken changes do not reach `develop`.

**Acceptance criteria**
- Given a PR that changes `database/`
  When CI runs
  Then migrations and seed are applied to a fresh PostgreSQL and the job fails on any error.
