"""Runtime system prompt and the human-approval keyword heuristic.

The curated, human-facing prompt templates live in docs/ai/prompt-library.md — this module is
the one actually sent to the LLM at request time, which implements the "cite only from context,
say insufficient context rather than fabricate" rule from docs/ai/governance.md.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are the mortgage knowledge assistant for an internal servicing platform.
Answer ONLY using the provided context chunks. Every factual claim must be traceable to one of
the chunks below.
If the context does not contain enough information to answer confidently, say so explicitly —
never invent policy, numbers, or procedures that are not in the context.
Keep answers concise (3-5 sentences) and written for a servicing agent, not a borrower.
Do not mention real borrower names or data; the corpus is synthetic."""


def build_user_prompt(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(f"[{i + 1}] {text}" for i, text in enumerate(context_chunks))
    return f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer using only the context above."


# Questions that ask the assistant to make or imply a decision (approve, waive, override, etc.)
# always require human sign-off per docs/ai/governance.md, regardless of retrieval confidence —
# this assistant explains policy, it never makes the decision itself.
DECISION_KEYWORDS = (
    "approve",
    "decline",
    "waive",
    "forbearance",
    "modification",
    "override",
    "exception",
)


def mentions_a_decision(question: str) -> bool:
    lowered = question.lower()
    return any(keyword in lowered for keyword in DECISION_KEYWORDS)
