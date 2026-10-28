# mortgage-knowledge-assistant

Python/FastAPI RAG assistant over the synthetic mortgage policy corpus (port **8001**, M7).
Pipeline: `Documents -> Chunking -> Embeddings -> Vector Store -> Retriever -> LLM -> Grounded Response`.

## Run locally

```bash
cd ai/mortgage-knowledge-assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.ingestion.ingest        # builds .index/vector_store.pkl from knowledge/v1/
uvicorn src.api.main:app --reload --port 8001
curl http://localhost:8001/health
```

Run tests: `pytest -v` (builds the vector store from the real corpus in-process — no index file
or network call needed).

## RAG defaults

| Setting | Value | Why |
| --- | --- | --- |
| Chunk size | 400 words | Approximates the spec's 512-token default (~1.3 tokens/word for English prose) without a tokenizer dependency |
| Chunk overlap | 50 words | Approximates the spec's 64-token default |
| Top-k | 5 | Spec default |
| Similarity threshold | **0.15** | Empirically tuned against this corpus's local TF-IDF backend — see "Why 0.15, not 0.7" below |

Tune via `CHUNK_SIZE_WORDS`, `CHUNK_OVERLAP_WORDS`, `TOP_K`, `SIMILARITY_THRESHOLD` (`.env.example`).

### Why 0.15, not the spec's 0.7

The spec's 0.7 default assumes real semantic embeddings, where a relevant chunk and a
differently-worded question still land close together in vector space. This service's default
backend is **local TF-IDF** (lexical overlap, not semantic) — chosen because it requires no API
key and costs nothing, so the service is fully runnable and testable with zero external
dependencies. TF-IDF cosine similarities between a short question and a paragraph-length chunk
are naturally much lower than semantic-embedding similarities even for a strong match. Empirical
testing against this corpus (documented in the M7 commit) found genuinely relevant matches
scoring 0.17-0.56 and off-topic questions scoring exactly 0.0 — so 0.15 cleanly separates the two
for this corpus. **If you switch to real OpenAI embeddings** (set `LLM_API_KEY`), re-tune this
threshold upward toward the spec's 0.7 — the two backends are not on the same scale.

## Embeddings and generation: same code, pluggable backend

Mirrors the `AWS_ENDPOINT_URL` pattern in `analytics/mortgage-analytics-service` and
`services/*/.../messaging`: the same code path either calls a real external API or falls back to
a free local implementation, selected by one env var.

| | `LLM_API_KEY` unset (default) | `LLM_API_KEY` set |
| --- | --- | --- |
| Embeddings | Local TF-IDF (`sklearn.TfidfVectorizer`) | OpenAI-compatible `/embeddings` (also works with Azure OpenAI via `LLM_API_BASE`) |
| Generation | Extractive: the answer is built directly from the retrieved chunk text, word for word — zero hallucination risk by construction | Real chat completion with a system prompt requiring cite-from-context-only (`src/generation/prompts.py`) |

No LLM API key is configured or available in this build environment, so the extractive path is
what's actually been run and tested end-to-end here. The OpenAI-compatible path is real,
complete code — it has not been exercised against a live API key, since none was available.

## Vector store

A plain in-memory cosine-similarity scan (`src/retrieval/vector_store.py`), not FAISS/Chroma/
pgvector. At this corpus's scale (27 chunks today) that's an exact, zero-infrastructure choice;
FAISS/Chroma would be the right call once the corpus grows into the thousands of chunks — a
future milestone, not needed yet.

## Ingest -> ask flow

1. Edit/add files under `knowledge/v1/` (see `knowledge/README.md` for corpus rules).
2. `python -m src.ingestion.ingest` — rebuilds `.index/vector_store.pkl` (gitignored; derived
   data, not committed).
3. `POST /api/v1/assistant/ask` — if no index file exists yet, the API builds one in memory at
   startup (slower first request, logged as a warning) so a fresh clone still works without a
   separate ingest step.

```bash
curl -X POST http://localhost:8001/api/v1/assistant/ask -H "Content-Type: application/json" \
  -d '{"question": "What happens when a payment is 30 days late?"}'
# -> answer + citations pointing at delinquency-playbook.md

curl -X POST http://localhost:8001/api/v1/assistant/ask -H "Content-Type: application/json" \
  -d '{"question": "What is the weather forecast for tomorrow?"}'
# -> insufficient-context answer, empty citations, requiresHumanApproval: true
```

## Human-in-the-loop

Any question matching a decision keyword (`approve`, `decline`, `waive`, `forbearance`,
`modification`, `override`, `exception` — see `src/generation/prompts.py`) sets
`requiresHumanApproval: true` even when retrieval confidence is high, because this assistant
explains policy, it never makes the decision itself. Full rules:
[docs/ai/governance.md](../../docs/ai/governance.md).

## Incident summarization (M7 task 7.6)

```bash
curl -X POST http://localhost:8001/api/v1/assistant/summarize-incident -H "Content-Type: application/json" \
  -d "{\"incidentText\": \"$(cat incidents/sample-incident-001.md | sed 's/"/\\"/g')\"}"
```

Flags `requiresHumanApproval: true` when the incident text doesn't mention a resolution or root
cause (heuristic — a real implementation would use the LLM's own confidence/reasoning).

## Auth (optional, M6)

If `JWT_SECRET` is set (must match `mortgage-service`'s value), every `/api/v1/assistant/*`
request requires `Authorization: Bearer <jwt>`. If unset, the API is open — fine for local dev,
not for anything exposed beyond `localhost`.

## Errors

Standard envelope (`code`, `message`, `correlationId`, `timestamp`), same as the Java and
analytics services.
