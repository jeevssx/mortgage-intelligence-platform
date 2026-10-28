# Delinquency Playbook

Synthetic servicing guidance for the secondary mortgage intelligence platform. Aligns with the
canonical delinquency rule in `guides/standards.md`.

## Timeline

A mortgage payment is due on the `due_date` of each billing period. If no successful payment
posts within 30 calendar days after the due date, the mortgage status changes from ACTIVE to
DELINQUENT. This 30-day threshold is the single source of truth for delinquency status across
the platform — the analytics service, the servicing service, and this playbook all use the same
rule. A mortgage that is 23 days past due is still ACTIVE, not DELINQUENT, because it has not yet
crossed the 30-day threshold.

When a mortgage becomes delinquent, the system fires a `LoanDelinquent` event and the servicing
team begins the borrower contact timeline:

- **Day 1-10 past due:** automated reminder notice (email and SMS), no agent call required.
- **Day 11-29 past due:** one courtesy call from a servicing agent, logged as a servicing history
  event with type `BORROWER_CONTACTED`.
- **Day 30 (delinquency triggers):** formal delinquency notice mailed; mortgage status flips to
  DELINQUENT; a servicing agent must attempt direct contact within 5 business days.
- **Day 45-60:** second formal notice; discuss repayment plan or forbearance options with the
  borrower.
- **Day 90+:** escalate to the risk analyst team for loss-mitigation review; this is outside the
  servicing agent's authority to resolve alone.

## Severity bands

Once a mortgage is DELINQUENT, severity is assigned based on days past due (DPD):

| Severity | Days past due |
| --- | --- |
| LOW | 30-44 |
| MODERATE | 45-59 |
| HIGH | 60-89 |
| SEVERE | 90+ |

Severity determines which team owns the account: servicing agents own LOW/MODERATE, risk
analysts are looped in at HIGH, and SEVERE cases require risk analyst sign-off before any
repayment plan is offered.

## Curing a delinquency

A delinquent mortgage cures (returns to ACTIVE) when the borrower brings the account fully
current — not partially current. A partial payment that does not cover all missed amounts plus
fees does not cure the delinquency; it only reduces the outstanding balance and is logged as a
`PAYMENT_POSTED` servicing history event without a status change. Only a payment (or series of
payments) that eliminates the full past-due amount triggers the cure and a status change back to
ACTIVE.

## What a servicing agent can and cannot do

A servicing agent can post payments, log contact attempts, and discuss standard repayment plans
for LOW/MODERATE severity. A servicing agent **cannot** approve a loan modification, waive fees
above the standard courtesy threshold, or make any forbearance decision for HIGH/SEVERE
accounts — those require risk analyst or underwriter sign-off per
`docs/ai/governance.md`.
