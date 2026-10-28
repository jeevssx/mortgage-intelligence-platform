"""FastAPI app factory.

Run: uvicorn src.api.main:app --reload --port 8001
Tests call create_app(...) with a prebuilt store/llm_client, so no ingestion or LLM API call is
needed to test the API layer.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from src.api.middleware import CorrelationIdMiddleware, register_exception_handlers
from src.api.routes import assistant, health
from src.config import Settings, get_settings
from src.generation.assistant_service import AssistantService
from src.generation.llm_client import create_llm_client
from src.ingestion.ingest import INDEX_PATH
from src.retrieval.embeddings import create_embedding_backend
from src.retrieval.vector_store import VectorStore
from src.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)

SERVICE_ROOT = Path(__file__).resolve().parents[2]


def create_app(
    settings: Settings | None = None,
    *,
    store: VectorStore | None = None,
    llm_client: Any | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.service_name, settings.log_level)

    if store is None:
        store = _load_or_build_store(settings)
    if llm_client is None:
        llm_client = create_llm_client(settings)

    app = FastAPI(
        title="Mortgage Knowledge Assistant",
        version="1.0.0",
        description="RAG assistant over synthetic mortgage policy/guidance documents.",
    )
    app.state.settings = settings
    app.state.assistant_service = AssistantService(store, llm_client, settings)

    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(assistant.router)
    return app


def _load_or_build_store(settings: Settings) -> VectorStore:
    if INDEX_PATH.exists():
        logger.info("Loading vector index from disk", extra={"path": str(INDEX_PATH)})
        return VectorStore.load(INDEX_PATH)

    logger.warning(
        "No vector index found; building in-memory at startup. "
        "Run `python -m src.ingestion.ingest` to persist it and speed up future startups.",
        extra={"expectedPath": str(INDEX_PATH)},
    )
    backend = create_embedding_backend(settings)
    return VectorStore.build(
        SERVICE_ROOT / settings.knowledge_dir,
        backend,
        size_words=settings.chunk_size_words,
        overlap_words=settings.chunk_overlap_words,
    )


def __getattr__(name: str) -> FastAPI:
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
