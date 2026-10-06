-- sample-queries.sql — Session 5 SQL lab artifacts for mortgage operations.
-- Run: psql -U mortgage_app -d mortgage_intel -f database/scripts/sample-queries.sql
-- EXPLAIN output and index rationale: docs/architecture/query-notes.md

\echo '== 1. Borrower-to-loan join: every mortgage with its borrower and loan terms =='
SELECT b.borrower_external_id,
       b.first_name || ' ' || b.last_name AS borrower_name,
       m.mortgage_external_id,
       m.status,
       l.loan_external_id,
       l.interest_rate,
       l.term_months,
       l.underwriting_decision
FROM borrower b
JOIN mortgage m ON m.borrower_id = b.id
LEFT JOIN loan l ON l.mortgage_id = m.id
ORDER BY b.borrower_external_id, m.mortgage_external_id;

\echo '== 2. Outstanding balance aggregation by status, and by borrower =='
SELECT status,
       COUNT(*)                  AS mortgages,
       SUM(outstanding_balance)  AS outstanding_total,
       ROUND(AVG(outstanding_balance), 2) AS outstanding_avg
FROM mortgage
GROUP BY status
ORDER BY status;

SELECT b.borrower_external_id,
       COUNT(m.id)                                        AS mortgages,
       SUM(m.outstanding_balance)                         AS outstanding_total,
       COUNT(*) FILTER (WHERE m.status = 'DELINQUENT')    AS delinquent_mortgages
FROM borrower b
JOIN mortgage m ON m.borrower_id = b.id
GROUP BY b.borrower_external_id
ORDER BY outstanding_total DESC;

\echo '== 3. Delinquent loans report =='
SELECT m.mortgage_external_id,
       b.borrower_external_id,
       m.outstanding_balance,
       d.delinquent_since,
       d.days_past_due,
       d.severity
FROM mortgage m
JOIN borrower b ON b.id = m.borrower_id
LEFT JOIN delinquency d ON d.mortgage_id = m.id
WHERE m.status = 'DELINQUENT'
ORDER BY d.days_past_due DESC;

\echo '== 3b. Delinquency rate (canonical formula) =='
SELECT ROUND(
         COUNT(*) FILTER (WHERE status = 'DELINQUENT')::numeric
         / NULLIF(COUNT(*) FILTER (WHERE status IN ('ACTIVE', 'DELINQUENT')), 0),
         4) AS delinquency_rate
FROM mortgage;

\echo '== 4. Delinquency batch candidates: installments unpaid 30+ days past due (as of 2026-02-24) =='
-- "Slow query" exercise. Without an index on due_date, PostgreSQL scans every payment row
-- (all POSTED history included) to find a handful of open installments. The partial index
-- idx_payment_open_due (migration 002) indexes only SCHEDULED/FAILED rows, so the batch
-- reads a tiny index regardless of how much posted history accumulates.
SELECT m.mortgage_external_id,
       MIN(p.due_date)                         AS oldest_unpaid_due,
       DATE '2026-02-24' - MIN(p.due_date)     AS days_past_due
FROM payment p
JOIN mortgage m ON m.id = p.mortgage_id
WHERE p.status IN ('SCHEDULED', 'FAILED')
  AND p.due_date <= DATE '2026-02-24' - 30
  AND NOT EXISTS (                 -- a later successful payment for the same installment cures it
        SELECT 1 FROM payment p2
        WHERE p2.mortgage_id = p.mortgage_id
          AND p2.due_date = p.due_date
          AND p2.status = 'POSTED')
GROUP BY m.mortgage_external_id
ORDER BY days_past_due DESC;

\echo '== 4b. EXPLAIN for the batch filter (seq scan disabled to show the plan used at scale) =='
SET enable_seqscan = off;
EXPLAIN (COSTS OFF)
SELECT mortgage_id, due_date
FROM payment
WHERE status IN ('SCHEDULED', 'FAILED')
  AND due_date <= DATE '2026-02-24' - 30;
RESET enable_seqscan;

\echo '== 5. Payment history timeline for one mortgage (uses idx_payment_mortgage_due) =='
SELECT p.due_date, p.paid_date, p.amount, p.status
FROM payment p
JOIN mortgage m ON m.id = p.mortgage_id
WHERE m.mortgage_external_id = 'MTG-1002'
ORDER BY p.due_date;

\echo '== 6. Demo ID check =='
SELECT mortgage_external_id, status
FROM mortgage
WHERE mortgage_external_id IN ('MTG-1001', 'MTG-1002')
ORDER BY mortgage_external_id;
