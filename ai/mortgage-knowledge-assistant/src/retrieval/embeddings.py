"""Embedding backends behind one interface: fit_transform(corpus) once at ingest, transform(query)
per request. Two implementations, selected by whether LLM_API_KEY is set (same "same code, real
API or local fallback" pattern as analytics-service's AWS_ENDPOINT_URL) — see README for why.
"""

from __future__ import annotations

from typing import Protocol

import httpx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.config import Settings
from src.utils.errors import UpstreamServiceError


class EmbeddingBackend(Protocol):
    def fit_transform(self, texts: list[str]) -> np.ndarray: ...

    def transform(self, texts: list[str]) -> np.ndarray: ...


class TfidfEmbeddingBackend:
    """Local, zero-cost fallback. No semantic understanding — purely lexical overlap — but
    deterministic, free, and good enough for a corpus of this size when questions share
    vocabulary with the source documents (true for this capstone's demo scenarios)."""

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._fitted = False

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        matrix = self._vectorizer.fit_transform(texts)
        self._fitted = True
        return matrix.toarray()

    def transform(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("fit_transform must be called (ingest) before transform (query)")
        return self._vectorizer.transform(texts).toarray()


class OpenAiEmbeddingBackend:
    """Calls an OpenAI-compatible embeddings endpoint (also works against Azure OpenAI by
    pointing LLM_API_BASE at the Azure resource URL)."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.llm_api_base
        self._api_key = settings.llm_api_key
        self._model = settings.embedding_model

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        return self.transform(texts)

    def transform(self, texts: list[str]) -> np.ndarray:
        try:
            response = httpx.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "input": texts},
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(f"Embedding API request failed: {exc}") from exc
        data = response.json()
        return np.array([item["embedding"] for item in data["data"]])


def create_embedding_backend(settings: Settings) -> EmbeddingBackend:
    if settings.llm_configured:
        return OpenAiEmbeddingBackend(settings)
    return TfidfEmbeddingBackend()
