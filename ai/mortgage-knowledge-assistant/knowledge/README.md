# Knowledge corpus

Source of truth for the `mortgage-knowledge-assistant` RAG pipeline. All content is **synthetic**
— no real borrower data, no real institutional policy. Versioned under `v1/`; a future revision
adds documents under `v2/` rather than editing `v1/` in place, so citations from an already-shipped
answer remain traceable to the exact text that generated them.

## Files (v1)

| File | Content |
| --- | --- |
| `mortgage-policy-overview.md` | Servicing policy summary: statuses, payment posting, document retention |
| `underwriting-guidelines.md` | Approval criteria: DTI, LTV, credit score bands, conditions |
| `delinquency-playbook.md` | The 30-day delinquency rule, severity bands, contact timeline, cure process |
| `servicing-faq.md` | Agent procedures: payment disputes, payoff quotes, escrow questions |
| `security-policy-excerpt.md` | Data classification and access rules referenced from `docs/security/security-controls.md` |

## Update process

1. Edit or add a file under `v1/` (or create `v2/` for a breaking revision — e.g. a rewritten
   delinquency rule that would invalidate old citations).
2. Re-run ingestion: `python -m src.ingestion.ingest` (see service README) to rebuild the vector
   index. The index is derived data, not committed — rebuild it after any corpus change.
3. Spot-check with `POST /api/v1/assistant/ask` using a question that should hit the new/changed
   section; confirm the citation `documentId`/`section` point at it.

## Rules

- No real borrower names, SSNs, account numbers, or addresses — ever. Use the same synthetic
  `MTG-####`/`BOR-###` conventions as the rest of the platform if an example ID is needed.
- Keep each document's `##` section headings stable once published — citations reference
  `(documentId, section, chunkId)`, and renaming a heading breaks the traceability of past answers.
