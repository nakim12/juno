"""Sample MMM output catalog (design doc 5.5, 5.6)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents import initial_analysis
from app.api.analysis import analysis_stream_response
from app.models.mmm_output import MMMOutput
from app.session.store import session_store

router = APIRouter(prefix="/api/samples", tags=["samples"])

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"


def _load_sample_file(sample_id: str) -> MMMOutput:
    path = SAMPLES_DIR / f"{sample_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found.")
    return MMMOutput.model_validate_json(path.read_text(encoding="utf-8"))


@router.get("")
def list_samples() -> list[dict]:
    """Return metadata for each bundled sample scenario."""
    out: list[dict] = []
    for path in sorted(SAMPLES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data.get("metadata", {})
        out.append(
            {
                "id": path.stem,
                "name": path.stem.replace("_", " ").title(),
                "model_type": meta.get("model_type"),
                "n_channels": len(data.get("channels", [])),
                "data_span_weeks": meta.get("data_span_weeks"),
            }
        )
    return out


@router.post("/{sample_id}/load")
async def load_sample(sample_id: str) -> dict:
    """Load a sample into a fresh session and run the initial analysis."""
    mmm = _load_sample_file(sample_id)
    session = session_store.create(mmm)
    summary, report = await initial_analysis.run(mmm, session.session_id)
    session.summary = summary
    session.report = report
    return {"session_id": session.session_id, "report": report.model_dump()}


@router.post("/{sample_id}/load/stream")
async def load_sample_stream(sample_id: str) -> StreamingResponse:
    """Streaming variant of :func:`load_sample` for a live report-building UX."""
    mmm = _load_sample_file(sample_id)
    session = session_store.create(mmm)
    return analysis_stream_response(session)
