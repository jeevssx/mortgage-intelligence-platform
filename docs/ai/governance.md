# AI governance (M7)

Human-in-the-loop rules for `mortgage-knowledge-assistant`. Prompt templates:
[prompt-library.md](./prompt-library.md). Implementation: `src/generation/`.

## Principle

This assistant **explains policy**; it never **makes a decision**. Loan approval, delinquency
severity escalation, fee waivers, and modification sign-off remain human decisions per
`knowledge/v1/underwriting-guidelines.md` and `knowledge/v1/delinquency-playbook.md` — the
assistant's job is to surface what those documents say, not to act on them.

## When a human must override / review the assistant

1. **Any question that mentions a decision action** (`approve`, `decline`, `waive`,
   `forbearance`, `modification`, `override`, `exception`) — `requiresHumanApproval: true` is
   set automatically regardless of retrieval confidence (`mentions_a_decision()` in
   `src/generation/prompts.py`). The answer still explains relevant policy; it does not take
   the decision.
2. **Retrieval confidence below the similarity threshold** — the assistant explicitly says it
   lacks reliable context rather than guessing, and flags `requiresHumanApproval: true` so the
   question routes to a person instead of being silently under-answered.
3. **Incident summaries that don't document a resolution or root cause** — flagged
   `requiresHumanApproval: true` so an engineer confirms the incident is actually closed rather
   than trusting an automated summary of an apparently-still-open issue.
4. **Any question touching a Restricted-tier data field** (date of birth, credentials — see
   `knowledge/v1/security-policy-excerpt.md`) — the assistant is not meant to be asked to
   disclose these at all; if a question's phrasing suggests that intent, treat it as a security
   concern per the escalation rule in that document, not a normal policy question.

## PII redaction rules

- The knowledge corpus itself contains **no real borrower data** — only synthetic examples
  using the platform's standard `MTG-####`/`BOR-###` ID conventions (see `knowledge/README.md`).
- Prompts and responses are logged with the structured logger
  (`src/utils/logging_config.py`), which logs the question/answer text and metadata
  (confidence, citation count) but never a raw API key or JWT.
- **Operational rule for anyone extending this service:** if a future version accepts
  borrower-specific context (e.g. a real mortgage's payment history) rather than only the
  static policy corpus, that context must be redacted to non-PII fields (status, dates,
  amounts) before it reaches the LLM prompt — never send name, email, phone, or date of birth
  to an external LLM API. This is not yet a concern today because the current corpus and
  question flow never include real borrower data in the first place.

## Hallucination controls (tested)

| Control | Mechanism | Verified by |
| --- | --- | --- |
| Cite-from-context-only system prompt | `SYSTEM_PROMPT` in `prompts.py` instructs the LLM to answer only from supplied chunks | Code review (prompt text); real-LLM-mode behavior not independently testable here — no LLM API key was available in this build environment |
| Insufficient-context fallback | If top retrieval score is below `SIMILARITY_THRESHOLD`, the service returns a fixed "I don't have reliable information..." answer with empty citations instead of calling the generator at all | `test_ask_off_topic_question_returns_insufficient_context` |
| Extractive default mode | With no LLM API key configured (this build's actual running mode), the "answer" is built directly from retrieved chunk text — it is structurally impossible for it to state anything not already in the corpus | `test_ask_relevant_question_returns_answer_with_citation`, live demo in `ai/mortgage-knowledge-assistant/README.md` |
| Citations traceable to real chunks | Every citation's `chunkId` is one the vector store actually produced at ingest time — there is no code path that fabricates a citation | `test_build_from_real_corpus_finds_the_right_document`, API tests asserting `citations[0].documentId` |
| Decision questions always flagged | `mentions_a_decision()` keyword check | `test_ask_decision_question_flags_human_approval_even_with_good_retrieval` |

**Honest limitation:** the "cite-from-context-only" system prompt is the control for *real LLM
mode*, and that mode has not been exercised against a live model in this environment (no API
key available) — a real LLM can still occasionally ignore a system prompt and partially
paraphrase beyond the context even when instructed not to ("instruction drift"). Before relying
on real LLM mode in a non-local environment, run a manual red-team pass asking several
out-of-corpus questions and confirming no fabricated specifics (dollar amounts, day counts,
rates) slip into the answer, the same way the extractive-mode tests already do for the default
configuration.
