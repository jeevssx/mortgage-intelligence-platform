"""In-memory cosine-similarity vector store.

Deliberately not FAISS/Chroma/pgvector: at this corpus's scale (dozens of chunks), a plain numpy
cosine-similarity scan is exact, has zero extra infrastructure, and is fast enough that an index
structure would only add complexity. The spec allows this as a team choice
(m07-ai-rag-assistant.md task 7.2); FAISS/Chroma would be the right call once the corpus grows
into the thousands of chunks.

Persisted to disk as a single pickle file so `ingest.py` and the running API process don't need
to share an embedding backend instance — loading restores the fitted TF-IDF vectorizer (or the
OpenAI backend config) exactly as it was at ingest time.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from src.ingestion.chunker import Chunk, chunk_sections
from src.ingestion.loader import load_document_sections
from src.retrieval.embeddings import EmbeddingBackend


class VectorStore:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, backend: EmbeddingBackend) -> None:
        self.chunks = chunks
        self.vectors = vectors
        self.backend = backend

    @classmethod
    def build(cls, knowledge_dir: Path, backend: EmbeddingBackend, *, size_words: int, overlap_words: int) -> "VectorStore":
        sections = load_document_sections(knowledge_dir)
        chunks = chunk_sections(sections, size_words=size_words, overlap_words=overlap_words)
        if not chunks:
            raise ValueError(f"No chunks produced from {knowledge_dir} — is the corpus empty?")
        vectors = backend.fit_transform([c.text for c in chunks])
        return cls(chunks, vectors, backend)

    def search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        query_vector = self.backend.transform([query])[0]
        scores = _cosine_similarity(self.vectors, query_vector)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.chunks[i], float(scores[i])) for i in top_indices]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path) -> "VectorStore":
        with path.open("rb") as f:
            return pickle.load(f)


def _cosine_similarity(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    matrix_norms = np.linalg.norm(matrix, axis=1)
    vector_norm = np.linalg.norm(vector)
    denom = matrix_norms * vector_norm
    with np.errstate(divide="ignore", invalid="ignore"):
        similarities = np.where(denom > 0, (matrix @ vector) / denom, 0.0)
    return similarities
