# Mortgage Policy Overview

Synthetic servicing policy summary for the secondary mortgage intelligence platform.

## Mortgage statuses

A mortgage moves through four statuses over its lifecycle:

- **PENDING** — underwriting is not yet complete; the loan has not been funded.
- **ACTIVE** — the mortgage is funded and payments are current (not delinquent).
- **DELINQUENT** — a payment is more than 30 calendar days past due; see the delinquency
  playbook for the full timeline and severity bands.
- **CLOSED** — the mortgage has been paid off in full, or the loan was declined before funding
  and the record is retained for audit purposes only.

A mortgage can move from ACTIVE to DELINQUENT and back to ACTIVE (when cured), but a CLOSED
mortgage never reopens — a new mortgage record is created if the borrower originates a new loan.

## Payment posting policy

Every payment is recorded with a `due_date`, an optional `paid_date`, an `amount`, and a status
of `SCHEDULED`, `POSTED`, `FAILED`, or `REVERSED`. Posting a payment with status `POSTED` reduces
the mortgage's outstanding balance by the payment amount. A `REVERSED` payment (for example, a
bounced check discovered after initial posting) adds the amount back to the outstanding balance
and should never be edited in place — it is always recorded as a new payment row with status
`REVERSED`, preserving the full history of what happened.

## Document retention

Mortgage documents (income verification, appraisals, title reports) are retained for the life of
the loan plus 7 years after closure, matching standard regulatory retention expectations for
mortgage servicing records. Documents are stored with metadata linking them to the
`mortgageExternalId` they belong to; a servicing agent should never delete a document record,
even after a mortgage closes.

## Who owns what decision

- **Underwriters** decide loan approval/decline and underwriting conditions.
- **Servicing agents** handle day-to-day payment posting, servicing history, and borrower
  communication for accounts that are ACTIVE or at LOW/MODERATE delinquency severity.
- **Risk analysts** own portfolio-level delinquency trends and any account at HIGH or SEVERE
  delinquency severity.
- **Administrators** manage user/role configuration, not loan decisions.

See `underwriting-guidelines.md` and `delinquency-playbook.md` for the detailed criteria behind
each of these roles' decisions.
