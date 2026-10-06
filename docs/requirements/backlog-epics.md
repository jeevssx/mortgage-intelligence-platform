# Backlog Epics

Epic names below are canonical. User stories in [user-stories.md](./user-stories.md) (M2) use these exact names and story ID prefixes.

| # | Epic | Story prefix | Primary milestone(s) |
| --- | --- | --- | --- |
| 1 | Borrower Management | `US-BOR` | M2, M4 |
| 2 | Mortgage Management | `US-MTG` | M2, M4 |
| 3 | Underwriting | `US-UW` | M4, M7 |
| 4 | Servicing | `US-SRV` | M4, M5 |
| 5 | Payment | `US-PAY` | M4, M5 |
| 6 | Delinquency | `US-DEL` | M2, M3, M4, M5 |
| 7 | Analytics | `US-ANL` | M3, M8 |
| 8 | Document Management | `US-DOC` | M3, M8 |
| 9 | Security | `US-SEC` | M2, M6 |
| 10 | AI Assistant | `US-AI` | M7 |
| 11 | Operations | `US-OPS` | M5, M9, M10 |

---

## Borrower Management

Maintains the parties on each loan: identity, contact details, and the business ID (`BOR-###`) used across every system. Accurate borrower records are the anchor for servicing contact, risk aggregation by borrower, and any future borrower-facing flows.

## Mortgage Management

Creates and maintains the mortgage as the servicing unit: original amount, outstanding balance, origination date, and lifecycle status. Every downstream capability (payments, servicing, delinquency, documents, analytics) keys off the mortgage business ID (`MTG-####`).

## Underwriting

Records the loan terms (rate, term) and the underwriting decision for each mortgage. It gives underwriters a consistent, auditable approve/decline outcome and, with the AI assistant, quick access to the policy guidance behind those decisions.

## Servicing

Keeps the chronological record of everything that happens to a loan after funding: onboarding, payments, status changes, borrower contact. Servicing agents rely on it to answer "what is the state of this loan and how did it get here," and compliance relies on it as an audit trail.

## Payment

Schedules and posts borrower payments and keeps outstanding balance correct. Idempotent payment posting prevents double-crediting when a client retries, which protects both the investor and the borrower.

## Delinquency

Detects missed payments using the canonical 30-day rule, tracks days past due and severity, and emits delinquency events. Early, consistent delinquency detection is the main lever for loss mitigation in a secondary-market portfolio.

## Analytics

Turns transactional data into portfolio intelligence: size, outstanding balance, delinquency rate, borrower risk concentration, and payment trends. Risk analysts use it to spot deteriorating segments before they become losses.

## Document Management

Stores loan documents (income verification, appraisals, disclosures) in object storage with metadata linked to the mortgage. It keeps loan files complete and retrievable for servicing, audits, and repurchase reviews, without putting binaries in the database.

## Security

Protects borrower data and platform integrity: role-based access per persona, secure transport across trust boundaries, secret management, threat modeling, and security testing. In a regulated mortgage context, this is a precondition for operating at all.

## AI Assistant

A retrieval-augmented assistant that answers questions about mortgage policy and servicing procedures, grounded in approved documents and citing its sources. It shortens the time underwriters and servicing agents spend searching guidelines, while refusing to answer outside its sources.

## Operations

Makes the platform deployable, observable, and supportable: containers, CI/CD with quality and security gates, Terraform infrastructure, dashboards, alerts, and runbooks. Support engineers use it to find and fix failures quickly using correlation IDs across services.
