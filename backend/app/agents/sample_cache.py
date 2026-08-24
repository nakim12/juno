"""On-disk cache of agent analysis reports for bundled sample scenarios.

The `/analyze` pipeline runs a live (paid) Claude call every time. Sample
outputs are fixed, so the first analysis of each sample is cached to disk and
replayed on subsequent loads — free, and still streamed for the live-building
UX. Uploaded (user) MMM outputs are never cached since they are unique.
"""

from __future__ import annotations

from pathlib import Path

from app.agents import prompts
from app.models.analysis_report import AnalysisReport

_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_analyses"

PROMPT_NAME = "analysis"


def _path(sample_id: str) -> Path:
    return _CACHE_DIR / f"{sample_id}.json"


def get(sample_id: str, *, allow_stale: bool = False) -> AnalysisReport | None:
    """Return the cached report for ``sample_id`` if present, valid, and current.

    A cached report is only reused when it was produced by the *current* prompt
    version; otherwise it is treated as stale so a prompt bump transparently
    regenerates (and never silently serves outdated output).

    ``allow_stale`` relaxes the version check for callers that have no way to
    regenerate — a demo deployment with no API key. There, a slightly outdated
    report is strictly better than a broken page, and it's labelled as
    pre-computed either way.
    """
    path = _path(sample_id)
    if not path.exists():
        return None
    try:
        report = AnalysisReport.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        # Corrupt or stale-schema cache entry: ignore and regenerate.
        return None
    if not allow_stale and report.metadata.prompt_version != prompts.version_tag(PROMPT_NAME):
        return None
    return report


def put(sample_id: str, report: AnalysisReport) -> Path:
    """Persist ``report`` as the cached analysis for ``sample_id``."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(sample_id)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path
