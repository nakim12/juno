"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor everything to the backend/ directory so files (the .env key, the Chroma
# index, the eval db) resolve identically no matter what working directory the
# process is launched from (e.g. uvicorn started with --app-dir, or from frontend/).
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_ROOT / ".env"


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

    # Embeddings: "local" (free MiniLM via Chroma) or "openai" (text-embedding-3-small)
    embedding_backend: Literal["local", "openai"] = "local"
    embedding_model: str = "text-embedding-3-small"

    # RAG
    chroma_persist_dir: str = str(_BACKEND_ROOT / "data" / "chroma")
    rag_top_k: int = 8
    rag_rerank_candidates: int = 20

    # Which retrieval backend to use. "auto" prefers the embedding model but
    # steps down to BM25 when the container is too small to load it without
    # being OOM-killed — see app/rag/retriever.py. Pin it explicitly to keep a
    # deployment's retrieval behaviour from depending on its memory limit.
    retrieval_backend: Literal["auto", "vector", "lexical"] = "auto"

    # Session
    session_ttl_seconds: int = 60 * 60 * 2  # 2 hours (design doc 5.7)

    # Demo mode. When on, visitor requests may never spend the server's API
    # credit: pre-computed sample analyses and chat answers are replayed from
    # disk, uploads are parsed but not interpreted, and live generation requires
    # the caller to supply their own key. The strongest version of this is to
    # simply not set ANTHROPIC_API_KEY on the public host at all — then no code
    # path can spend anything, whatever this flag says.
    demo_mode: bool = True

    # Rate limiting. Applies only to calls billed to the server's own key; a
    # caller spending their own key is not throttled. The global cap is the
    # wallet backstop, since a per-IP limit alone bounds nothing when IPs are
    # trivially rotated. Tune via env on deploy.
    rate_limit_enabled: bool = True
    rate_limit_per_ip_per_hour: int = 20
    rate_limit_global_per_day: int = 150

    # Evaluation
    eval_db_path: str = str(_BACKEND_ROOT / "data" / "eval.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
