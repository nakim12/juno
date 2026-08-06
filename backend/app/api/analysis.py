"""Analysis endpoints (design doc 5.6, 7.1)."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents import initial_analysis
from app.models.mmm_output import MMMOutput
from app.session.store import Session, session_store

router = APIRouter(prefix="/api", tags=["analysis"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def analysis_stream_response(session: Session) -> StreamingResponse:
    """Run the analysis pipeline for ``session`` and stream progress over SSE.

    Emits fast stages first (parsed channels, retrieved knowledge sources), then
    generation progress, then the final report. The summary and report are
    persisted on the session as they are produced.
    """

    async def event_gen():
        chars = 0
        async for kind, payload in initial_analysis.run_streaming(
            session.mmm_output, session.session_id
        ):
            if kind == "summary":
                session.summary = payload
                yield _sse(
                    "summary",
                    {
                        "model_type": payload.model_type,
                        "n_channels": payload.n_channels,
                        "channels": [c.name for c in payload.channels],
                        "detected_issues": [i.code for i in payload.detected_issues],
                    },
                )
            elif kind == "sources":
                yield _sse(
                    "sources", {"sources": [s.model_dump() for s in payload]}
                )
            elif kind == "token":
                # Forward generation progress as a running character count rather
                # than raw JSON so the client can show a live activity indicator.
                chars += len(payload)
                yield _sse("progress", {"chars": chars})
            elif kind == "report":
                session.report = payload
                yield _sse(
                    "report",
                    {
                        "session_id": session.session_id,
                        "report": payload.model_dump(),
                    },
                )
        yield _sse("done", {})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/analyze")
async def analyze(mmm: MMMOutput) -> dict:
    """Create a session from an uploaded MMM output and run the analysis pipeline."""
    session = session_store.create(mmm)
    summary, report = await initial_analysis.run(mmm, session.session_id)
    session.summary = summary
    session.report = report
    return {"session_id": session.session_id, "report": report.model_dump()}


@router.post("/analyze/stream")
async def analyze_streaming(mmm: MMMOutput) -> StreamingResponse:
    """Streaming variant of :func:`analyze` for a live report-building UX."""
    session = session_store.create(mmm)
    return analysis_stream_response(session)


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
