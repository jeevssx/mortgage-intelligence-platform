-- seed_mortgage_data.sql
-- Synthetic dev/demo portfolio. NO REAL PII: names are invented, emails use example.test,
-- phones use the 555 exchange.
--
-- Snapshot date: 2026-02-24. days_past_due values are as of that date
-- (the servicing batch in M4/M5 recalculates them).
--
-- Re-runnable: truncates all domain tables first. Dev/test only. Run as mortgage_owner
-- after migrations.
--
-- Reserved IDs (not seeded; used by the M4 create-API demo): BOR-010, MTG-1010, LOAN-2010.

\set ON_ERROR_STOP on

BEGIN;

TRUNCATE document, delinquency, servicing_history, payment, loan, mortgage, borrower;

-- ---------------------------------------------------------------------------
-- Borrowers (8)
-- ---------------------------------------------------------------------------
INSERT INTO borrower (borrower_external_id, first_name, last_name, email, phone, date_of_birth) VALUES
  ('BOR-001', 'Jamie',   'Nguyen',   'jamie.nguyen@example.test',   '+1-555-1001', '1985-03-20'),
  ('BOR-002', 'Morgan',  'Lee',      'morgan.lee@example.test',     '+1-555-1002', '1990-11-02'),
  ('BOR-003', 'Riley',   'Okafor',   'riley.okafor@example.test',   '+1-555-1003', '1978-07-14'),
  ('BOR-004', 'Casey',   'Delgado',  'casey.delgado@example.test',  '+1-555-1004', '1982-01-09'),
  ('BOR-005', 'Avery',   'Kowalski', 'avery.kowalski@example.test', '+1-555-1005', '1970-09-30'),
  ('BOR-006', 'Quinn',   'Haddad',   'quinn.haddad@example.test',   '+1-555-1006', '1994-05-22'),
  ('BOR-007', 'Rowan',   'Mbeki',    'rowan.mbeki@example.test',    '+1-555-1007', '1988-12-03'),
  ('BOR-008', 'Harper',  'Lindqvist','harper.lindqvist@example.test','+1-555-1008', '1965-04-17');

-- ---------------------------------------------------------------------------
-- Mortgages (12): 6 ACTIVE, 3 DELINQUENT, 1 PENDING, 2 CLOSED
-- ---------------------------------------------------------------------------
INSERT INTO mortgage (mortgage_external_id, borrower_id, status, original_amount, outstanding_balance, origination_date)
SELECT v.mtg, b.id, v.status, v.orig, v.bal, v.orig_date::date
FROM (VALUES
  -- mtg,       borrower,  status,       original,  outstanding, origination
  ('MTG-1001', 'BOR-001', 'ACTIVE',     310000.00, 305000.00, '2024-01-15'),  -- on-time payer (primary demo)
  ('MTG-1002', 'BOR-002', 'DELINQUENT', 280000.00, 279000.00, '2023-06-01'),  -- 45 DPD (primary delinquent demo)
  ('MTG-1003', 'BOR-001', 'ACTIVE',     425000.00, 425000.00, '2026-01-20'),  -- recently onboarded, first payment not yet due
  ('MTG-1004', 'BOR-003', 'ACTIVE',     360000.00, 318400.00, '2022-04-01'),  -- Feb payment 23 days late: not yet delinquent
  ('MTG-1005', 'BOR-004', 'DELINQUENT', 240000.00, 198750.00, '2021-08-15'),  -- 85 DPD after a failed payment
  ('MTG-1006', 'BOR-005', 'ACTIVE',     500000.00, 412300.00, '2020-02-01'),  -- on-time payer
  ('MTG-1007', 'BOR-006', 'ACTIVE',     275000.00, 268900.00, '2024-07-01'),  -- on-time payer
  ('MTG-1008', 'BOR-007', 'DELINQUENT', 330000.00, 321500.00, '2023-03-15'),  -- 40 DPD
  ('MTG-1009', 'BOR-002', 'PENDING',    295000.00, 295000.00, '2026-02-10'),  -- in underwriting
  ('MTG-1011', 'BOR-008', 'CLOSED',     220000.00,      0.00, '2019-05-01'),  -- paid off Oct 2025
  ('MTG-1012', 'BOR-008', 'ACTIVE',     180000.00, 178900.00, '2025-11-01'),  -- failed + reversed payments, cured in grace
  ('MTG-1013', 'BOR-003', 'CLOSED',     410000.00,      0.00, '2026-01-05')   -- underwriting declined, never funded
) AS v(mtg, bor, status, orig, bal, orig_date)
JOIN borrower b ON b.borrower_external_id = v.bor;

-- ---------------------------------------------------------------------------
-- Loans (1:1 with mortgage)
-- ---------------------------------------------------------------------------
INSERT INTO loan (loan_external_id, mortgage_id, interest_rate, term_months, underwriting_decision)
SELECT v.loan, m.id, v.rate, v.term, v.decision
FROM (VALUES
  ('LOAN-2001', 'MTG-1001', 0.0625, 360, 'APPROVED'),
  ('LOAN-2002', 'MTG-1002', 0.0675, 360, 'APPROVED'),
  ('LOAN-2003', 'MTG-1003', 0.0599, 360, 'APPROVED'),
  ('LOAN-2004', 'MTG-1004', 0.0450, 360, 'APPROVED'),
  ('LOAN-2005', 'MTG-1005', 0.0375, 360, 'APPROVED'),
  ('LOAN-2006', 'MTG-1006', 0.0325, 360, 'APPROVED'),
  ('LOAN-2007', 'MTG-1007', 0.0650, 360, 'APPROVED'),
  ('LOAN-2008', 'MTG-1008', 0.0700, 360, 'APPROVED'),
  ('LOAN-2009', 'MTG-1009', 0.0625, 360, 'PENDING'),
  ('LOAN-2011', 'MTG-1011', 0.0425, 180, 'APPROVED'),
  ('LOAN-2012', 'MTG-1012', 0.0675, 240, 'APPROVED'),
  ('LOAN-2013', 'MTG-1013', 0.0725, 360, 'DECLINED')
) AS v(loan, mtg, rate, term, decision)
JOIN mortgage m ON m.mortgage_external_id = v.mtg;

-- ---------------------------------------------------------------------------
-- Payments
-- On-time = paid within the 15-day grace period (paid_date <= due_date + 15).
-- ---------------------------------------------------------------------------

-- On-time histories (Sep 2025 – Feb 2026), next installment SCHEDULED.
INSERT INTO payment (mortgage_id, due_date, paid_date, amount, status)
SELECT m.id, d::date, d::date + v.paid_offset, v.amount, 'POSTED'
FROM (VALUES
  ('MTG-1001', 1750.00,  2, DATE '2025-09-01', DATE '2026-02-01'),
  ('MTG-1006', 2990.00, -2, DATE '2025-09-01', DATE '2026-02-01'),
  ('MTG-1007', 1700.00,  3, DATE '2025-09-15', DATE '2026-02-15'),
  ('MTG-1004', 2150.00,  5, DATE '2025-09-01', DATE '2026-01-01'),
  ('MTG-1002', 1650.00,  4, DATE '2025-09-10', DATE '2025-12-10'),
  ('MTG-1008', 2050.00,  1, DATE '2025-09-15', DATE '2025-12-15')
) AS v(mtg, amount, paid_offset, first_due, last_paid_due)
JOIN mortgage m ON m.mortgage_external_id = v.mtg
CROSS JOIN LATERAL generate_series(v.first_due, v.last_paid_due, INTERVAL '1 month') AS d;

-- Unpaid / future installments.
INSERT INTO payment (mortgage_id, due_date, paid_date, amount, status)
SELECT m.id, v.due::date, NULL, v.amount, 'SCHEDULED'
FROM (VALUES
  ('MTG-1001', '2026-03-01', 1750.00),
  ('MTG-1006', '2026-03-01', 2990.00),
  ('MTG-1007', '2026-03-15', 1700.00),
  ('MTG-1003', '2026-03-01', 2545.00),  -- first payment, not yet due
  ('MTG-1004', '2026-02-01', 2150.00),  -- 23 days past due on snapshot date (< 30: still ACTIVE)
  ('MTG-1002', '2026-01-10', 1650.00),  -- missed: 45 DPD
  ('MTG-1002', '2026-02-10', 1650.00),  -- missed
  ('MTG-1008', '2026-01-15', 2050.00),  -- missed: 40 DPD
  ('MTG-1008', '2026-02-15', 2050.00),  -- missed
  ('MTG-1005', '2026-01-01', 1480.00),  -- missed
  ('MTG-1005', '2026-02-01', 1480.00)   -- missed
) AS v(mtg, due, amount)
JOIN mortgage m ON m.mortgage_external_id = v.mtg;

-- MTG-1005: late payments, then an NSF failure that starts delinquency (85 DPD from 2025-12-01).
INSERT INTO payment (mortgage_id, due_date, paid_date, amount, status)
SELECT m.id, v.due::date, v.paid::date, v.amount, v.status
FROM (VALUES
  ('2025-09-01', '2025-09-04', 1480.00, 'POSTED'),
  ('2025-10-01', '2025-10-21', 1480.00, 'POSTED'),  -- late (outside grace)
  ('2025-11-01', '2025-11-26', 1480.00, 'POSTED'),  -- late (outside grace)
  ('2025-12-01', NULL,         1480.00, 'FAILED')   -- returned NSF
) AS v(due, paid, amount, status)
JOIN mortgage m ON m.mortgage_external_id = 'MTG-1005';

-- MTG-1011: paid off in October 2025.
INSERT INTO payment (mortgage_id, due_date, paid_date, amount, status)
SELECT m.id, v.due::date, v.paid::date, v.amount, 'POSTED'
FROM (VALUES
  ('2025-09-01', '2025-09-01',  1655.00),
  ('2025-10-01', '2025-10-01',  1655.00),
  ('2025-10-20', '2025-10-20', 41250.00)   -- payoff
) AS v(due, paid, amount)
JOIN mortgage m ON m.mortgage_external_id = 'MTG-1011';

-- MTG-1012: failed and reversed attempts, each cured within the grace period.
INSERT INTO payment (mortgage_id, due_date, paid_date, amount, status)
SELECT m.id, v.due::date, v.paid::date, v.amount, v.status
FROM (VALUES
  ('2025-12-01', '2025-12-01', 1365.00, 'POSTED'),
  ('2026-01-01', NULL,         1365.00, 'FAILED'),
  ('2026-01-01', '2026-01-06', 1365.00, 'POSTED'),
  ('2026-02-01', '2026-02-02', 1365.00, 'REVERSED'),  -- posted, then bank reversal
  ('2026-02-01', '2026-02-09', 1365.00, 'POSTED'),
  ('2026-03-01', NULL,         1365.00, 'SCHEDULED')
) AS v(due, paid, amount, status)
JOIN mortgage m ON m.mortgage_external_id = 'MTG-1012';

-- ---------------------------------------------------------------------------
-- Delinquency snapshots (one row per DELINQUENT mortgage)
-- delinquent_since = due date of the oldest unpaid installment.
-- Severity bands: 30-59 MODERATE, 60-89 HIGH, 90+ SEVERE.
-- ---------------------------------------------------------------------------
INSERT INTO delinquency (mortgage_id, delinquent_since, days_past_due, severity)
SELECT m.id, v.since::date, v.dpd, v.severity
FROM (VALUES
  ('MTG-1002', '2026-01-10', 45, 'MODERATE'),
  ('MTG-1005', '2025-12-01', 85, 'HIGH'),
  ('MTG-1008', '2026-01-15', 40, 'MODERATE')
) AS v(mtg, since, dpd, severity)
JOIN mortgage m ON m.mortgage_external_id = v.mtg;

-- ---------------------------------------------------------------------------
-- Servicing history
-- ---------------------------------------------------------------------------
INSERT INTO servicing_history (mortgage_id, event_time, event_type, description)
SELECT m.id, v.ts::timestamptz, v.event_type, v.description
FROM (VALUES
  ('MTG-1001', '2024-01-20T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1001', '2026-01-03T09:30:00Z', 'PAYMENT_POSTED',      'Payment 1750.00 posted'),
  ('MTG-1001', '2026-02-03T09:30:00Z', 'PAYMENT_POSTED',      'Payment 1750.00 posted'),
  ('MTG-1002', '2023-06-05T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1002', '2025-12-14T09:30:00Z', 'PAYMENT_POSTED',      'Payment 1650.00 posted'),
  ('MTG-1002', '2026-01-26T08:00:00Z', 'PAYMENT_MISSED',      'Installment due 2026-01-10 unpaid after grace period'),
  ('MTG-1002', '2026-01-28T15:10:00Z', 'BORROWER_CONTACT',    'Outbound call; left voicemail'),
  ('MTG-1002', '2026-02-09T08:00:00Z', 'STATUS_CHANGED',      'ACTIVE -> DELINQUENT (30+ days past due)'),
  ('MTG-1003', '2026-01-25T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1004', '2022-04-06T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1004', '2026-02-17T08:00:00Z', 'PAYMENT_MISSED',      'Installment due 2026-02-01 unpaid after grace period'),
  ('MTG-1005', '2021-08-20T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1005', '2025-12-03T11:00:00Z', 'PAYMENT_FAILED',      'Payment 1480.00 returned NSF'),
  ('MTG-1005', '2025-12-17T08:00:00Z', 'PAYMENT_MISSED',      'Installment due 2025-12-01 unpaid after grace period'),
  ('MTG-1005', '2025-12-31T08:00:00Z', 'STATUS_CHANGED',      'ACTIVE -> DELINQUENT (30+ days past due)'),
  ('MTG-1005', '2026-01-30T08:00:00Z', 'DELINQUENCY_UPDATED', 'Severity MODERATE -> HIGH (60+ days past due)'),
  ('MTG-1006', '2020-02-05T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1007', '2024-07-05T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1008', '2023-03-20T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1008', '2026-01-31T08:00:00Z', 'PAYMENT_MISSED',      'Installment due 2026-01-15 unpaid after grace period'),
  ('MTG-1008', '2026-02-14T08:00:00Z', 'STATUS_CHANGED',      'ACTIVE -> DELINQUENT (30+ days past due)'),
  ('MTG-1009', '2026-02-10T14:00:00Z', 'APPLICATION_RECEIVED','Mortgage application received; underwriting pending'),
  ('MTG-1011', '2019-05-06T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1011', '2025-10-20T12:00:00Z', 'LOAN_PAID_OFF',       'Payoff 41250.00 received; lien release requested'),
  ('MTG-1011', '2025-10-21T08:00:00Z', 'STATUS_CHANGED',      'ACTIVE -> CLOSED'),
  ('MTG-1012', '2025-11-05T10:00:00Z', 'ONBOARDING_COMPLETE', 'Mortgage onboarded to servicing'),
  ('MTG-1012', '2026-01-02T11:00:00Z', 'PAYMENT_FAILED',      'Payment 1365.00 failed: card declined'),
  ('MTG-1012', '2026-02-04T11:00:00Z', 'PAYMENT_REVERSED',    'Payment 1365.00 reversed by bank'),
  ('MTG-1013', '2026-01-05T14:00:00Z', 'APPLICATION_RECEIVED','Mortgage application received'),
  ('MTG-1013', '2026-01-19T16:00:00Z', 'UNDERWRITING_DECLINED','Declined: debt-to-income above policy limit')
) AS v(mtg, ts, event_type, description)
JOIN mortgage m ON m.mortgage_external_id = v.mtg;

-- ---------------------------------------------------------------------------
-- Document metadata (binaries not stored; S3 keys follow the M3 convention)
-- ---------------------------------------------------------------------------
INSERT INTO document (mortgage_id, document_type, s3_key, file_name)
SELECT m.id, v.doc_type, 'mortgages/' || v.mtg || '/' || v.uuid || '-' || v.file_name, v.file_name
FROM (VALUES
  ('MTG-1001', 'INCOME_VERIFICATION', '0b1f3c2e-6d4a-4f7e-9a1b-2c3d4e5f6a01', 'paystub-redacted.pdf'),
  ('MTG-1001', 'APPRAISAL',           '0b1f3c2e-6d4a-4f7e-9a1b-2c3d4e5f6a02', 'appraisal-report.pdf'),
  ('MTG-1002', 'INCOME_VERIFICATION', '0b1f3c2e-6d4a-4f7e-9a1b-2c3d4e5f6a03', 'w2-2024-redacted.pdf'),
  ('MTG-1002', 'HARDSHIP_LETTER',     '0b1f3c2e-6d4a-4f7e-9a1b-2c3d4e5f6a04', 'hardship-letter.pdf'),
  ('MTG-1003', 'CLOSING_DISCLOSURE',  '0b1f3c2e-6d4a-4f7e-9a1b-2c3d4e5f6a05', 'closing-disclosure.pdf'),
  ('MTG-1009', 'INCOME_VERIFICATION', '0b1f3c2e-6d4a-4f7e-9a1b-2c3d4e5f6a06', 'paystub-redacted.pdf'),
  ('MTG-1011', 'LIEN_RELEASE',        '0b1f3c2e-6d4a-4f7e-9a1b-2c3d4e5f6a07', 'lien-release.pdf')
) AS v(mtg, doc_type, uuid, file_name)
JOIN mortgage m ON m.mortgage_external_id = v.mtg;

COMMIT;
