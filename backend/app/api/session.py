"""Session rehydration endpoint (design doc 5.6)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.session.store import session_store

router = APIRouter(prefix="/api/session", tags=["session"])


@router.get("/{session_id}")
def get_session(session_id: str) -> dict:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return {
        "session_id": session.session_id,
        "summary": session.summary.model_dump() if session.summary else None,
        "report": session.report.model_dump() if session.report else None,
        "history": [m.model_dump() for m in session.history],
    }
