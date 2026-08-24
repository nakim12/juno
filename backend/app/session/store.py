"""In-memory session store with TTL (design doc 5.7).

Swap this for a Redis-backed implementation in production; the interface is
deliberately small so that migration is a drop-in change.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from app.core.config import settings
from app.models.analysis_report import AnalysisReport
from app.models.chat_message import ChatMessage
from app.models.mmm_output import MMMOutput
from app.models.mmm_summary import MMMSummary


@dataclass
class Session:
    session_id: str
    mmm_output: MMMOutput
    # Set when the session came from a bundled sample. Uploads leave it None.
    # Chat uses it to find that sample's pre-computed answers.
    sample_id: str | None = None
    summary: MMMSummary | None = None
    report: AnalysisReport | None = None
    history: list[ChatMessage] = field(default_factory=list)
    retrieval_logs: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def is_expired(self, ttl_seconds: int) -> bool:
        return (time.time() - self.created_at) > ttl_seconds


class SessionStore:
    """Simple process-local session store keyed by session id."""

    def __init__(self, ttl_seconds: int = settings.session_ttl_seconds) -> None:
        self._sessions: dict[str, Session] = {}
        self._ttl = ttl_seconds

    def create(self, mmm_output: MMMOutput, sample_id: str | None = None) -> Session:
        self._evict_expired()
        session_id = uuid.uuid4().hex
        session = Session(
            session_id=session_id, mmm_output=mmm_output, sample_id=sample_id
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired(self._ttl):
            self._sessions.pop(session_id, None)
            return None
        return session

    def _evict_expired(self) -> None:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired(self._ttl)]
        for sid in expired:
            self._sessions.pop(sid, None)


# Module-level singleton used by the API layer.
session_store = SessionStore()
