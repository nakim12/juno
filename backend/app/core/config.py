"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve backend/.env relative to this file so the key loads regardless of the
# process working directory (e.g. when uvicorn is started with --app-dir).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_name: str = "Juno"
    environment: Literal["dev", "prod"] = "dev"
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""  # used for embeddings only

    # Model selection (see design doc section 6)
    agent_model: str = "claude-sonnet-4-5"
    judge_model: str = "claude-opus-4-5"
    embedding_model: str = "text-embedding-3-small"

    # RAG
    chroma_persist_dir: str = "./data/chroma"
    rag_top_k: int = 8
    rag_rerank_candidates: int = 20

    # Session
    session_ttl_seconds: int = 60 * 60 * 2  # 2 hours (design doc 5.7)

    # Evaluation
    eval_db_path: str = "./data/eval.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
