"""Analysis endpoints (design doc 5.6, 7.1)."""

from __future__ import annotations

import json
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.agents import initial_analysis
from app.core.caller_key import LLMAccess, llm_access
from app.core.llm import LLMClient
from app.core.rate_limit import llm_rate_limit
from app.models.analysis_report import AnalysisReport
from app.models.mmm_output import MMMOutput
from app.parsers import mmm_parser
from app.session.store import Session, session_store

router = APIRouter(prefix="/api", tags=["analysis"])


def _require_generation(access: LLMAccess) -> None:
    """Reject interpretation requests that nobody is willing to pay for."""
    if access.can_generate:
        return
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=(
            "This demo doesn't run live analysis on uploads. Your file was "
            "parsed locally — add your own Anthropic API key to generate the "
            "written interpretation, or try a bundled sample."
        ),
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def summary_payload(summary) -> dict:
    """Flattened parse result. Shared by the SSE `summary` event and /parse so
    the client renders both through the same code path."""
    return {
        "model_type": summary.model_type,
        "n_channels": summary.n_channels,
        "channels": [c.name for c in summary.channels],
        "detected_issues": [i.code for i in summary.detected_issues],
    }


def analysis_stream_response(
    session: Session,
    *,
    cached_report: AnalysisReport | None = None,
    on_report: Callable[[AnalysisReport], None] | None = None,
    llm: LLMClient | None = None,
) -> StreamingResponse:
    """Run the analysis pipeline for ``session`` and stream progress over SSE.

    Emits fast stages first (parsed channels, retrieved knowledge sources), then
    generation progress, then the final report. The summary and report are
    persisted on the session as they are produced.

    If ``cached_report`` is given, it is replayed (no LLM call) through the same
    staged events. ``on_report`` is invoked with the final report once produced
    (used to populate the sample cache after a live run).
    """

    async def event_gen():
        chars = 0
        stream = (
            initial_analysis.replay_streaming(
                session.mmm_output, session.session_id, cached_report
            )
            if cached_report is not None
            else initial_analysis.run_streaming(
                session.mmm_output, session.session_id, llm=llm
            )
        )
        async for kind, payload in stream:
            if kind == "summary":
                session.summary = payload
                yield _sse("summary", summary_payload(payload))
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
                if on_report is not None:
                    on_report(payload)
                yield _sse(
                    "report",
                    {
                        "session_id": session.session_id,
                        "report": payload.model_dump(),
                    },
                )
        yield _sse("done", {})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/parse")
async def parse_only(mmm: MMMOutput) -> dict:
    """Parse an uploaded MMM output without interpreting it.

    Fully deterministic and free — no LLM call. This is what the public demo
    offers for uploads: a visitor still sees their own model parsed, ranked, and
    checked for structural issues, and only the written interpretation requires
    a key.
    """
    session = session_store.create(mmm)
    summary = mmm_parser.parse(mmm)
    session.summary = summary
    return {"session_id": session.session_id, "summary": summary_payload(summary)}


@router.post("/analyze")
async def analyze(
    mmm: MMMOutput, request: Request, access: LLMAccess = Depends(llm_access)
) -> dict:
    """Create a session from an uploaded MMM output and run the analysis pipeline."""
    _require_generation(access)
    if access.billed_to_server:
        await llm_rate_limit(request)

    session = session_store.create(mmm)
    summary, report = await initial_analysis.run(
        mmm, session.session_id, llm=access.agent_llm()
    )
    session.summary = summary
    session.report = report
    return {"session_id": session.session_id, "report": report.model_dump()}


@router.post("/analyze/stream")
async def analyze_streaming(
    mmm: MMMOutput, request: Request, access: LLMAccess = Depends(llm_access)
) -> StreamingResponse:
    """Streaming variant of :func:`analyze` for a live report-building UX."""
    _require_generation(access)
    if access.billed_to_server:
        await llm_rate_limit(request)

    session = session_store.create(mmm)
    return analysis_stream_response(session, llm=access.agent_llm())


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
