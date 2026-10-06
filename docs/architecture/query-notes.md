# Query Notes

Index rationale and `EXPLAIN` output for queries in [`database/scripts/sample-queries.sql`](../../database/scripts/sample-queries.sql). Captured on PostgreSQL 16.4 with the seed data loaded.

## Slow query exercise: delinquency batch candidates

The delinquency batch (M4) runs daily and needs "open installments whose due date is 30+ days ago":

```sql
SELECT mortgage_id, due_date
FROM payment
WHERE status IN ('SCHEDULED', 'FAILED')
  AND due_date <= DATE '2026-02-24' - 30;
```

### Before: no suitable index

`idx_payment_mortgage_due (mortgage_id, due_date)` leads with `mortgage_id`, so it cannot narrow a range filter on `due_date` alone. With sequential scans disabled, the best the planner can do is walk the **entire** composite index, checking `due_date` on every entry and then filtering `status` on the heap (otherwise it does a plain `Seq Scan`):

```text
Index Scan using idx_payment_mortgage_due on payment
  Index Cond: (due_date <= '2026-01-25'::date)
  Filter: ((status)::text = ANY ('{SCHEDULED,FAILED}'::text[]))
```

Either way, cost grows linearly with total payment history. A 100k-loan portfolio accumulates over a million `POSTED` rows a year, all of which the batch would read to find a few thousand open installments.

### After: partial index (migration 002)

```sql
CREATE INDEX idx_payment_open_due
    ON payment(due_date, mortgage_id)
    WHERE status IN ('SCHEDULED', 'FAILED');
```

```text
Bitmap Heap Scan on payment
  Recheck Cond: ((due_date <= '2026-01-25'::date) AND ((status)::text = ANY ('{SCHEDULED,FAILED}'::text[])))
  ->  Bitmap Index Scan on idx_payment_open_due
        Index Cond: (due_date <= '2026-01-25'::date)
```

**Why partial:** only open installments are indexed. Posted history never enters the index, so it stays small and cheap to maintain on the hot `POSTED` insert path. `mortgage_id` is included so the batch can group by mortgage without extra heap lookups for the key.

> With only 55 seed rows the planner rightly prefers a sequential scan; the plan above was captured with `SET enable_seqscan = off` to show the plan PostgreSQL uses at production volume. Re-check with `EXPLAIN (ANALYZE, BUFFERS)` on a larger synthetic dataset in M10 performance testing.

## Other index justifications

| Index | Query it serves |
| --- | --- |
| `idx_mortgage_borrower` | Borrower portfolio / risk summary (`JOIN mortgage ON borrower_id`) |
| `idx_mortgage_status` | Delinquent loans report, status queues (`WHERE status = 'DELINQUENT'`) |
| `idx_payment_mortgage_due` | Payment timeline for one mortgage, ordered by due date (query 5) |
| `idx_servicing_mortgage_time` | Servicing history API, chronological per mortgage |
| `idx_document_mortgage` | Document list per mortgage |
| `idx_borrower_email_lower` | Agent lookup by email, case-insensitive (`WHERE lower(email) = lower($1)`) |
