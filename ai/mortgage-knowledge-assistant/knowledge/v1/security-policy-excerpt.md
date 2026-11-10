# Security Policy Excerpt

Synthetic excerpt of the platform's security policy, for agent-facing questions about data
handling. Full technical detail lives in `docs/security/security-controls.md` — this document
is the plain-language version for the knowledge assistant's audience.

## Data classification

Borrower data is classified into four tiers:

- **Public** — nothing about a borrower's mortgage is public.
- **Internal** — business identifiers like the mortgage external ID and status; not secret, but
  not shared outside the platform's authenticated users.
- **Confidential** — name, email, phone number; personally identifiable but not high-risk on
  its own.
- **Restricted** — date of birth, and anything that could be used for identity verification or
  fraud. Password hashes and authentication tokens are also Restricted.

## What a servicing agent may discuss with a borrower

An agent may confirm a borrower's own mortgage status, balance, and payment history after
verifying identity through the standard verification questions (not covered in this excerpt).
An agent may never read back a borrower's date of birth or any other Restricted-tier field as a
"confirmation" step — those fields are used to *verify* the caller's identity, not to be
disclosed to whoever is on the call.

## Credentials and tokens

No one — agent, underwriter, or administrator — should ever ask a borrower for their mortgage
platform login credentials; borrowers do not have logins to this internal platform at all, only
staff do. Any request that sounds like asking a borrower for a password or access token is a
social engineering attempt and should be treated as a security incident, not a normal servicing
question.

## When to escalate a security concern

Escalate immediately (do not attempt to resolve yourself) if: a caller claims to be a borrower
but fails identity verification and pushes back, a caller asks how to access another borrower's
account, or you suspect a colleague's credentials have been compromised. See
`docs/ai/governance.md` for the escalation path.
