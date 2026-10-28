from pathlib import Path

import numpy as np

from src.ingestion.chunker import Chunk
from src.retrieval.embeddings import TfidfEmbeddingBackend
from src.retrieval.vector_store import VectorStore

REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeBackend:
    """Deterministic one-hot-ish backend so similarity math is exact and easy to assert on."""

    _VOCAB = {"alpha": 0, "beta": 1, "gamma": 2}

    def fit_transform(self, texts):
        return self.transform(texts)

    def transform(self, texts):
        matrix = np.zeros((len(texts), len(self._VOCAB)))
        for i, text in enumerate(texts):
            for word in text.lower().split():
                if word in self._VOCAB:
                    matrix[i, self._VOCAB[word]] += 1
        return matrix


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, document_id="d.md", title="D", section="S", text=text)


def test_search_ranks_by_cosine_similarity():
    chunks = [_chunk("c-1", "alpha alpha"), _chunk("c-2", "beta"), _chunk("c-3", "gamma gamma gamma")]
    backend = FakeBackend()
    vectors = backend.fit_transform([c.text for c in chunks])
    store = VectorStore(chunks, vectors, backend)

    results = store.search("alpha", top_k=3)

    assert results[0][0].chunk_id == "c-1"
    assert results[0][1] > results[1][1] >= results[2][1]


def test_search_handles_zero_vector_query_without_nan():
    chunks = [_chunk("c-1", "alpha")]
    backend = FakeBackend()
    vectors = backend.fit_transform([c.text for c in chunks])
    store = VectorStore(chunks, vectors, backend)

    results = store.search("unrelated-word-not-in-vocab", top_k=1)

    assert results[0][1] == 0.0


def test_save_and_load_round_trip(tmp_path):
    chunks = [_chunk("c-1", "alpha"), _chunk("c-2", "beta")]
    backend = FakeBackend()
    vectors = backend.fit_transform([c.text for c in chunks])
    store = VectorStore(chunks, vectors, backend)

    path = tmp_path / "store.pkl"
    store.save(path)
    loaded = VectorStore.load(path)

    assert [c.chunk_id for c in loaded.chunks] == ["c-1", "c-2"]
    assert loaded.search("alpha", top_k=1)[0][0].chunk_id == "c-1"


def test_build_from_real_corpus_finds_the_right_document():
    knowledge_dir = REPO_ROOT / "knowledge" / "v1"
    store = VectorStore.build(knowledge_dir, TfidfEmbeddingBackend(), size_words=400, overlap_words=50)

    results = store.search("What happens when a payment is 30 days late?", top_k=3)

    assert results[0][0].document_id == "delinquency-playbook.md"
    assert results[0][1] >= 0.15


def test_build_rejects_empty_corpus(tmp_path):
    try:
        VectorStore.build(tmp_path, TfidfEmbeddingBackend(), size_words=400, overlap_words=50)
        assert False, "expected ValueError"
    except ValueError:
        pass
