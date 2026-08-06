"""Cache of agent analysis reports per benchmark case.

Judge validation (reliability / test-retest) needs to score the *same* agent
outputs repeatedly. Running the agent is expensive (~1-2 min/case), so its
reports are cached to disk keyed by case id and reused across judge repetitions.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.agents import initial_analysis
from app.core.llm import LLMClient
from app.evaluation.benchmark_generator import BENCHMARKS_DIR, BenchmarkCase
from app.models.analysis_report import AnalysisReport


def _reports_path(version: str) -> Path:
    return BENCHMARKS_DIR / f"reports_{version}.json"


def load_reports(version: str = "v1") -> dict[str, AnalysisReport]:
    path = _reports_path(version)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {cid: AnalysisReport.model_validate(r) for cid, r in raw.items()}


def save_reports(reports: dict[str, AnalysisReport], version: str = "v1") -> Path:
    path = _reports_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({cid: r.model_dump() for cid, r in reports.items()}, indent=2),
        encoding="utf-8",
    )
    return path


async def get_reports(
    cases: list[BenchmarkCase], version: str = "v1", use_llm: bool = True
) -> dict[str, AnalysisReport]:
    """Return {case_id: AnalysisReport}, generating and caching any missing ones."""
    cache = load_reports(version)
    missing = [c for c in cases if c.case_id not in cache]
    if missing:
        agent_llm = None if use_llm else LLMClient(api_key="")
        for case in missing:
            _, report = await initial_analysis.run(
                case.mmm_output, session_id=case.case_id, llm=agent_llm
            )
            cache[case.case_id] = report
        save_reports(cache, version)
    return {c.case_id: cache[c.case_id] for c in cases if c.case_id in cache}
