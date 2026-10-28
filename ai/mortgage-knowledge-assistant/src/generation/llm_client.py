"""LLM generation: a real OpenAI-compatible chat completion if LLM_API_KEY is set, otherwise a
deterministic extractive fallback (the answer is built directly from the retrieved context, word
for word) — see .env.example and README for why this keeps the service runnable with zero cost.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from src.config import Settings
from src.generation.prompts import SYSTEM_PROMPT, build_user_prompt
from src.utils.errors import UpstreamServiceError


class LlmClient(Protocol):
    def generate(self, question: str, context_chunks: list[str]) -> str: ...


class OpenAiLlmClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.llm_api_base
        self._api_key = settings.llm_api_key
        self._model = settings.llm_model

    def generate(self, question: str, context_chunks: list[str]) -> str:
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": build_user_prompt(question, context_chunks)},
                    ],
                    "temperature": 0.2,
                },
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(f"LLM API request failed: {exc}") from exc
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class ExtractiveLlmClient:
    """No LLM configured: build the answer directly from the single most relevant chunk. Zero
    hallucination risk by construction — every word is already in the corpus."""

    _MAX_SENTENCES = 3

    def generate(self, question: str, context_chunks: list[str]) -> str:
        if not context_chunks:
            return "No relevant context was found for this question."
        sentences = _split_sentences(context_chunks[0])
        return " ".join(sentences[: self._MAX_SENTENCES]).strip()


def _split_sentences(text: str) -> list[str]:
    # Good enough for this corpus's prose; not meant to handle abbreviations perfectly.
    parts = [p.strip() for p in text.replace("\n", " ").split(". ")]
    return [p if p.endswith(".") else f"{p}." for p in parts if p]


def create_llm_client(settings: Settings) -> LlmClient:
    if settings.llm_configured:
        return OpenAiLlmClient(settings)
    return ExtractiveLlmClient()
