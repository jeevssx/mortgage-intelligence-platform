"""Service configuration loaded from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    service_name: str = "mortgage-knowledge-assistant"
    log_level: str = "INFO"
    server_port: int = 8001

    chunk_size_words: int = 400
    chunk_overlap_words: int = 50
    top_k: int = 5
    similarity_threshold: float = 0.15
    knowledge_dir: str = "knowledge/v1"

    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    jwt_secret: str | None = None

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        env = os.environ.get
        return cls(
            service_name=env("SERVICE_NAME", cls.service_name),
            log_level=env("LOG_LEVEL", cls.log_level).upper(),
            server_port=int(env("SERVER_PORT", str(cls.server_port))),
            chunk_size_words=int(env("CHUNK_SIZE_WORDS", str(cls.chunk_size_words))),
            chunk_overlap_words=int(env("CHUNK_OVERLAP_WORDS", str(cls.chunk_overlap_words))),
            top_k=int(env("TOP_K", str(cls.top_k))),
            similarity_threshold=float(env("SIMILARITY_THRESHOLD", str(cls.similarity_threshold))),
            knowledge_dir=env("KNOWLEDGE_DIR", cls.knowledge_dir),
            llm_api_base=env("LLM_API_BASE", cls.llm_api_base),
            llm_api_key=env("LLM_API_KEY") or None,
            llm_model=env("LLM_MODEL", cls.llm_model),
            embedding_model=env("EMBEDDING_MODEL", cls.embedding_model),
            jwt_secret=env("JWT_SECRET") or None,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
