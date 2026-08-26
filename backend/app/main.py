"""Juno backend entrypoint (FastAPI).

Run locally:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, chat, diagnostics, evaluation, samples, session
from app.core.config import settings

app = FastAPI(
    title="Juno API",
    description="Agentic copilot for interpreting Marketing Mix Model outputs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)
app.include_router(chat.router)
app.include_router(session.router)
app.include_router(samples.router)
app.include_router(evaluation.router)
app.include_router(diagnostics.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
