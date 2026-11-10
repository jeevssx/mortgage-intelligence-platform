# RCA template

Copy this into `docs/operations/rca-YYYY-MM-DD.md` for each incident
(`docs/operations/incident-response.md`).

## 1. Summary

One paragraph: what broke, for how long, who/what was affected.

## 2. Impact

Users/services affected, duration, which SLO (if any) was breached (`docs/operations/slo.md`).

## 3. Timeline (UTC)

Real timestamps, not approximations — pull them from the actual logs
(`correlationId`-tagged JSON, `guides/standards.md`).

## 4. Root cause

Technical root cause, plus contributing factors (what made it worse, or what made it take longer
to detect/fix than it should have).

## 5. Corrective actions

What was done to resolve this specific incident. Owner + date for each.

## 6. Preventive actions

What changes (monitoring, tests, runbook updates, architecture) reduce the chance of recurrence
or shorten detection/recovery time next time. Owner + date for each — an RCA with no preventive
action is blame without a fix.
