# Servicing FAQ

Synthetic agent procedures for common servicing questions on the secondary mortgage
intelligence platform.

## How do I handle a payment dispute?

When a borrower disputes a payment (claims they paid but the system shows no record, or
disputes the amount applied), a servicing agent should:

1. Pull the full payment history via `GET /api/v1/mortgages/{id}/payments` and compare against
   the borrower's claim.
2. Check for a pending or failed payment with a matching amount and approximate date — a
   `FAILED` status often explains a borrower's belief that they paid.
3. If the dispute cannot be resolved by the records alone, log a servicing history event with
   type `PAYMENT_DISPUTE_OPENED` and escalate to a risk analyst. Do not reverse or modify a
   payment record based on a borrower's verbal claim alone.
4. Never promise a specific resolution timeline to the borrower beyond "within 5 business days
   for research," since the actual investigation timeline depends on the risk analyst's queue.

## How do I provide a payoff quote?

A payoff quote is the exact amount required to fully satisfy the mortgage on a specific date. To
generate one: take the current `outstanding_balance`, add any accrued interest through the
requested payoff date, and add any outstanding fees. Payoff quotes are valid for 10 calendar
days from issuance because accrued interest changes daily. Never quote a payoff amount without
specifying the date it's valid through.

## How do I answer an escrow question?

Escrow covers property taxes and homeowner's insurance collected as part of the monthly payment
and held until those bills are due. Common borrower questions:

- **"Why did my payment go up?"** — usually an escrow shortage from a property tax or insurance
  increase; the servicer re-analyzes escrow annually and spreads any shortage over 12 months.
- **"Can I waive escrow?"** — only if the mortgage's LTV is at or below 80% and the borrower has
  a documented history of on-time tax/insurance payments; this requires underwriter sign-off, a
  servicing agent cannot approve an escrow waiver alone.

## What do I do if a borrower requests a loan modification?

A servicing agent can discuss the *existence* of loan modification programs and collect the
borrower's financial hardship documentation, but cannot approve a modification. Per the
delinquency playbook, modification decisions for DELINQUENT accounts at HIGH or SEVERE severity
require risk analyst review; for accounts that are still ACTIVE or at LOW/MODERATE severity, an
underwriter must still sign off before any change to loan terms takes effect.

## What do I do if I'm not sure what to tell a borrower?

Never guess. If a question falls outside documented procedure (this FAQ, the delinquency
playbook, or the underwriting guidelines), tell the borrower you'll follow up rather than
improvising an answer — see the escalation rules in `docs/ai/governance.md`.
