"""Analysis endpoints (design doc 5.6, 7.1)."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents import initial_analysis
from app.models.mmm_output import MMMOutput
from app.session.store import session_store

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze")
async def analyze(mmm: MMMOutput) -> dict:
    """Create a session from an uploaded MMM output and run the analysis pipeline."""
    session = session_store.create(mmm)
    summary, report = await initial_analysis.run(mmm, session.session_id)
    session.summary = summary
    session.report = report
    return {"session_id": session.session_id, "report": report.model_dump()}


@router.get("/analyze/{session_id}/stream")
async def analyze_stream(session_id: str) -> StreamingResponse:
    """Stream the cached report section-by-section as Server-Sent Events.

    The heavy lifting happens in :func:`analyze`; this endpoint replays the
    cached report progressively for the report view's streaming UX.
    """
    session = session_store.get(session_id)
    if session is None or session.report is None:
        raise HTTPException(status_code=404, detail="Session or report not found.")

    report = session.report

    async def event_gen():
        sections = [
            ("overview", report.overview),
            ("per_channel", [c.model_dump() for c in report.per_channel]),
            ("structural_risks", [r.model_dump() for r in report.structural_risks]),
            ("recommendations", [r.model_dump() for r in report.recommendations]),
            ("validation_suggestions", [v.model_dump() for v in report.validation_suggestions]),
        ]
        for name, payload in sections:
            yield f"event: section\ndata: {json.dumps({'section': name, 'content': payload})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
