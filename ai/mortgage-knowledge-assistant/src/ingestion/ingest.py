"""Rebuilds the vector index from the knowledge corpus.

Run: python -m src.ingestion.ingest
(from ai/mortgage-knowledge-assistant/, with the venv active)

The index is derived data (ai/mortgage-knowledge-assistant/.index/vector_store.pkl), not
committed — rebuild it after any corpus change (see knowledge/README.md).
"""

from __future__ import annotations

from pathlib import Path

from src.config import get_settings
from src.retrieval.embeddings import create_embedding_backend
from src.retrieval.vector_store import VectorStore

SERVICE_ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = SERVICE_ROOT / ".index" / "vector_store.pkl"


def main() -> None:
    settings = get_settings()
    knowledge_dir = SERVICE_ROOT / settings.knowledge_dir
    backend = create_embedding_backend(settings)

    store = VectorStore.build(
        knowledge_dir,
        backend,
        size_words=settings.chunk_size_words,
        overlap_words=settings.chunk_overlap_words,
    )
    store.save(INDEX_PATH)

    by_document: dict[str, int] = {}
    for chunk in store.chunks:
        by_document[chunk.document_id] = by_document.get(chunk.document_id, 0) + 1

    print(f"Indexed {len(store.chunks)} chunks from {knowledge_dir} -> {INDEX_PATH}")
    for doc_id, count in sorted(by_document.items()):
        print(f"  {doc_id}: {count} chunks")
    print(f"Embedding backend: {type(backend).__name__}")


if __name__ == "__main__":
    main()
