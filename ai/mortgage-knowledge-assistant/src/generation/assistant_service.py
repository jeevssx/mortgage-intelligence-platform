"""Orchestrates retrieval + generation for POST /api/v1/assistant/ask and the incident
summarization endpoint. See docs/architecture (pipeline): Documents -> Chunking -> Embeddings ->
Vector Store -> Retriever -> LLM -> Grounded Response.
"""

from __future__ import annotations

from src.config import Settings
from src.generation.llm_client import LlmClient
from src.generation.prompts import mentions_a_decision
from src.models.schemas import AskResponse, Citation, IncidentSummaryResponse
from src.retrieval.vector_store import VectorStore

_INSUFFICIENT_CONTEXT_ANSWER = (
    "I don't have reliable information in the knowledge base to answer this question "
    "confidently. Please consult a human expert or the full policy documents directly."
)


class AssistantService:
    def __init__(self, store: VectorStore, llm_client: LlmClient, settings: Settings) -> None:
        self._store = store
        self._llm_client = llm_client
        self._settings = settings

    def ask(self, question: str) -> AskResponse:
        results = self._store.search(question, self._settings.top_k)
        top_score = results[0][1] if results else 0.0

        if top_score < self._settings.similarity_threshold:
            return AskResponse(
                answer=_INSUFFICIENT_CONTEXT_ANSWER,
                citations=[],
                confidence=round(top_score, 4),
                requiresHumanApproval=True,
            )

        relevant = [(chunk, score) for chunk, score in results if score >= self._settings.similarity_threshold]
        context_texts = [chunk.text for chunk, _ in relevant]
        answer = self._llm_client.generate(question, context_texts)

        requires_approval = mentions_a_decision(question)
        if requires_approval:
            answer += (
                " (This touches a decision that requires human sign-off per "
                "docs/ai/governance.md — this answer explains policy only.)"
            )

        return AskResponse(
            answer=answer,
            citations=[
                Citation(documentId=chunk.document_id, section=chunk.section, chunkId=chunk.chunk_id)
                for chunk, _ in relevant
            ],
            confidence=round(top_score, 4),
            requiresHumanApproval=requires_approval,
        )

    def summarize_incident(self, incident_text: str) -> IncidentSummaryResponse:
        # Reuses the same generator, with an incident-specific instruction as the "question" and
        # the incident text itself as the only context chunk — no retrieval needed, the whole
        # incident report IS the context.
        prompt = (
            "Summarize this incident in 2-3 sentences covering what happened, impact, and the "
            "key follow-up action. Then note whether it appears fully resolved or still needs "
            "follow-up."
        )
        summary = self._llm_client.generate(prompt, [incident_text])

        low_confidence = "resolved" not in incident_text.lower() and "root cause" not in incident_text.lower()
        return IncidentSummaryResponse(
            summary=summary,
            recommendedRunbookLinks=[
                "docs/operations/messaging-runbook.md",
                "docs/operations/runbook.md",
            ],
            confidence=0.4 if low_confidence else 0.75,
            requiresHumanApproval=low_confidence,
        )
