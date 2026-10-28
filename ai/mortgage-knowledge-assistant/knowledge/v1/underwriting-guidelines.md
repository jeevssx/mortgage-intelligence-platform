# Underwriting Guidelines

Synthetic approval criteria for the secondary mortgage intelligence platform. Used by
underwriters when reviewing a loan's `underwriting_decision` (`PENDING`, `APPROVED`, `DECLINED`).

## Debt-to-income (DTI) ratio

DTI is total monthly debt obligations divided by gross monthly income.

- **DTI at or below 36%:** meets standard approval criteria with no additional conditions.
- **DTI 36-43%:** conditionally approvable if the borrower has at least 2 months of reserves and
  a credit score of 680 or higher.
- **DTI above 43%:** requires a compensating factor (large down payment, significant reserves,
  or co-borrower income) and underwriter manager sign-off; cannot be approved by a single
  underwriter alone.

## Loan-to-value (LTV) ratio

LTV is the loan amount divided by the appraised property value.

- **LTV at or below 80%:** no mortgage insurance required.
- **LTV 80.01-95%:** private mortgage insurance (PMI) required until the borrower reaches 80% LTV
  through payments or appreciation.
- **LTV above 95%:** requires a specialty loan program; outside standard conventional
  underwriting criteria covered by this guideline.

## Credit score bands

| Credit score | Underwriting treatment |
| --- | --- |
| 740+ | Best-tier pricing, minimal documentation review |
| 680-739 | Standard conventional underwriting |
| 620-679 | Manual underwriting review required; no automated approval |
| Below 620 | Does not meet conventional approval criteria; refer to a government-backed program outside this platform's scope |

## Conditions before final approval

Even a loan that meets DTI/LTV/credit criteria is not approved until these are verified:

1. Income documentation (pay stubs, W-2s, or tax returns for self-employed borrowers) matches
   the stated income within 5%.
2. No undisclosed debts appear on a final credit pull within 10 days of closing.
3. The property appraisal supports the loan amount at the stated LTV.
4. Title search shows no liens that would take priority over this mortgage.

If any condition fails, the underwriter moves the loan back to `PENDING` with a documented
reason rather than declining outright, unless the failure is clearly disqualifying (e.g. the
appraisal comes in well below the purchase price with no ability to cure).

## What requires underwriter manager escalation

A single underwriter can approve or decline within standard DTI/LTV/credit bands. Escalation to
an underwriter manager is required for: DTI above 43% without a clear compensating factor, any
loan amount above $750,000, or any loan where the borrower has a prior delinquency on another
mortgage in this platform within the last 24 months.
