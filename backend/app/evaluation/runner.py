"""Benchmark runner (design doc 5.4, 7.3, 9.1).

Iterates benchmark cases through the agent, scores each on the six design-doc
dimensions (deterministic where ground truth allows, LLM-judged otherwise),
logs failures, aggregates metrics, and persists the run for dashboard trending.

Supports a deterministic, LLM-free mode (``use_llm=False``) so the full harness
can be exercised without API cost: the agent falls back to its heuristic report
and only the deterministic dimensions (accuracy, calibration, failure-mode
recall) are computed.
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field

from app.agents import initial_analysis, prompts
from app.core.config import settings
from app.core.llm import LLMClient
from app.evaluation import metrics
from app.evaluation.benchmark_generator import BenchmarkCase
from app.evaluation.failure_catalog import FailureEntry, log_failure
from app.evaluation.judge import judge_response
from app.evaluation.metrics import DimensionScores
from app.evaluation.reference import get_references
from app.evaluation.results_store import (
    CalibrationPoint,
    RunRecord,
    save_calibration_points,
    save_run,
)
from app.models.analysis_report import AnalysisReport
from app.parsers import mmm_parser

FAILURE_THRESHOLD = 3.0  # judge dimensions below this get catalogued
# Judge dimensions we trust the LLM for; accuracy/calibration/failure detection
# are scored deterministically against ground truth instead.
_JUDGE_DIMS = ("groundedness", "actionability", "hallucination")


@dataclass
class CaseResult:
    case_id: str
    accuracy: float
    failure_recall: float | None
    confidences: list[float]
    correct: list[bool]
    judge_scores: dict[str, int] = field(default_factory=dict)
    scenario: dict = field(default_factory=dict)
    calib_records: list[metrics.CalibrationRecord] = field(default_factory=list)
    error: str | None = None


def _unconfigured_llm() -> LLMClient:
    """An LLM client with no key, forcing the agent's heuristic fallback path."""
    return LLMClient(api_key="")


async def run_case(
    case: BenchmarkCase,
    reference: str,
    run_id: str,
    use_llm: bool,
    use_judge: bool,
    cached_report: AnalysisReport | None = None,
) -> CaseResult:
    # When a cached agent report is supplied we skip the (expensive) agent call
    # and only re-score it. The summary is a deterministic parse of the model
    # output, so all non-judge metrics are recomputed for free; only the judge
    # (Opus) incurs cost. This powers cheap re-judge runs after a scoring change.
    if cached_report is not None:
        summary = mmm_parser.parse(case.mmm_output)
        report = cached_report
        initial_analysis._ensure_ranking(report, summary)
        return await _score_case(
            case, summary, report, reference, run_id, use_judge
        )

    agent_llm = None if use_llm else _unconfigured_llm()
    try:
        summary, report = await initial_analysis.run(
            case.mmm_output, session_id=case.case_id, llm=agent_llm
        )
    except Exception as exc:  # noqa: BLE001 — one bad case must not kill the suite
        # Record the agent failure as a catalogued failure and continue. This is
        # itself a failure mode worth measuring (e.g. truncated/invalid output).
        log_failure(
            FailureEntry(
                run_id=run_id,
                case_id=case.case_id,
                category="agent_error",
                agent_response="(agent raised before producing a report)",
                judge_reasoning=f"{type(exc).__name__}: {exc}",
                score=0.0,
            )
        )
        return CaseResult(
            case_id=case.case_id,
            accuracy=0.0,
            failure_recall=None,
            confidences=[],
            correct=[],
            scenario=case.scenario,
            error=f"{type(exc).__name__}: {exc}",
        )

    return await _score_case(case, summary, report, reference, run_id, use_judge)


async def _score_case(
    case: BenchmarkCase,
    summary,
    report: AnalysisReport,
    reference: str,
    run_id: str,
    use_judge: bool,
) -> CaseResult:
    """Compute all dimensions for a (summary, report) pair.

    Shared by the fresh-agent path and the cached-report re-judge path so both
    score identically. Only the judge call (when ``use_judge``) costs money.
    """
    # Accuracy measures the AGENT'S ranking judgment (report.channel_ranking),
    # not the raw parsed ROI ordering — the pipeline guarantees the ranking is
    # complete over exactly the model's channels.
    agent_ranking = report.channel_ranking
    truth_ranking = case.ground_truth.true_ranking()
    accuracy = metrics.spearman_rank_correlation(agent_ranking, truth_ranking)

    detected = metrics.detected_failure_modes(summary, report)
    recall = metrics.failure_mode_recall(
        case.ground_truth.known_failure_modes, detected
    )

    calib_records = metrics.calibration_records(report, case.ground_truth.true_roi)
    confidences = [r.prob for r in calib_records]
    correct = [r.correct for r in calib_records]

    judge_scores: dict[str, int] = {}
    if use_judge:
        try:
            verdict = await judge_response(
                ground_truth=str(case.ground_truth),
                reference=reference,
                agent_response=report.model_dump_json(),
            )
        except Exception as exc:  # noqa: BLE001 — judge hiccup shouldn't kill the run
            print(f"  judge failed for {case.case_id}: {exc}", file=sys.stderr, flush=True)
            verdict = None
        for dim in (verdict.scores if verdict else []):
            judge_scores[dim.dimension] = dim.score
            if dim.dimension in _JUDGE_DIMS and dim.score < FAILURE_THRESHOLD:
                log_failure(
                    FailureEntry(
                        run_id=run_id,
                        case_id=case.case_id,
                        category=dim.dimension,
                        agent_response=report.overview,
                        judge_reasoning=dim.reasoning,
                        score=float(dim.score),
                    )
                )

    return CaseResult(
        case_id=case.case_id,
        accuracy=accuracy,
        failure_recall=recall,
        confidences=confidences,
        correct=correct,
        judge_scores=judge_scores,
        scenario=case.scenario,
        calib_records=calib_records,
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _scenario_breakdown(results: list[CaseResult]) -> dict:
    """Mean accuracy grouped by channel-count bucket and by failure mode."""
    by_channels: dict[str, list[float]] = {}
    by_failure: dict[str, list[float]] = {}
    for r in results:
        n = r.scenario.get("n_channels", 0)
        bucket = "3-5" if n <= 5 else ("6-8" if n <= 8 else "9-10")
        by_channels.setdefault(bucket, []).append(r.accuracy)
        for fm in r.scenario.get("failure_modes", []):
            by_failure.setdefault(fm, []).append(r.failure_recall or 0.0)
    return {
        "accuracy_by_channel_count": {k: round(_mean(v), 4) for k, v in by_channels.items()},
        "recall_by_failure_mode": {k: round(_mean(v), 4) for k, v in by_failure.items()},
    }


async def run_suite(
    cases: list[BenchmarkCase],
    *,
    use_llm: bool = True,
    use_judge: bool = True,
    version: str = "v1",
    persist: bool = True,
    concurrency: int = 4,
    cached_reports: dict[str, AnalysisReport] | None = None,
) -> RunRecord:
    """Run the full benchmark suite and return the aggregated run record.

    Cases are independent, so up to ``concurrency`` run in parallel (the LLM
    client retries rate limits, so parallelism speeds wall-clock without wasting
    spend). Set ``concurrency=1`` for strictly sequential execution.

    If ``cached_reports`` is supplied ({case_id: AnalysisReport}), the agent is
    not called for those cases — the reports are re-scored in place. Combined
    with ``use_judge=True`` this performs a cheap judge-only re-run (only Opus
    judge calls cost money), used to refresh the snapshot after a scoring change.
    """
    references = (
        await get_references(cases, version, concurrency=concurrency) if use_judge else {}
    )
    record = RunRecord(
        n_cases=len(cases),
        accuracy=0.0,
        calibration_ece=0.0,
        groundedness=0.0,
        actionability=0.0,
        failure_mode_recall=0.0,
        hallucination_rate=0.0,
        weighted_total=0.0,
        agent_model=settings.agent_model if use_llm else "heuristic-fallback",
        judge_model=settings.judge_model if use_judge else "none",
        prompt_version=prompts.version_tag("analysis"),
        used_llm=use_llm,
        used_judge=use_judge,
    )

    total = len(cases)
    sem = asyncio.Semaphore(max(1, concurrency))
    completed = 0

    async def _run_one(index: int, case: BenchmarkCase) -> tuple[int, CaseResult]:
        nonlocal completed
        async with sem:
            t0 = time.time()
            result = await run_case(
                case,
                reference=references.get(case.case_id, ""),
                run_id=record.run_id,
                use_llm=use_llm,
                use_judge=use_judge,
                cached_report=(cached_reports or {}).get(case.case_id),
            )
            completed += 1
            status = f"ERROR ({result.error})" if result.error else (
                f"acc={result.accuracy:.3f} "
                f"recall={result.failure_recall if result.failure_recall is not None else '—'}"
            )
            print(
                f"[{completed}/{total}] {case.case_id} {status} ({time.time() - t0:.1f}s)",
                file=sys.stderr,
                flush=True,
            )
            return index, result

    gathered = await asyncio.gather(
        *(_run_one(i, case) for i, case in enumerate(cases))
    )
    # Restore original case order (gather completes out of order under concurrency).
    results: list[CaseResult] = [r for _, r in sorted(gathered, key=lambda x: x[0])]

    all_conf = [c for r in results for c in r.confidences]
    all_correct = [c for r in results for c in r.correct]
    recalls = [r.failure_recall for r in results if r.failure_recall is not None]

    scores = DimensionScores(
        accuracy=_mean([r.accuracy for r in results]),
        calibration=metrics.expected_calibration_error(all_conf, all_correct),
        failure_mode_recall=_mean(recalls),
    )
    if use_judge:
        scores.groundedness = _mean(
            [r.judge_scores["groundedness"] for r in results if "groundedness" in r.judge_scores]
        ) / 5.0
        scores.actionability = _mean(
            [r.judge_scores["actionability"] for r in results if "actionability" in r.judge_scores]
        )
        # Hallucination is a response-level RATE: the fraction of responses the
        # judge flags as containing a material (invented/unsupported) claim —
        # not 1 - mean_score/5, which penalized ordinary imperfection.
        hall_scores = [
            r.judge_scores["hallucination"]
            for r in results
            if "hallucination" in r.judge_scores
        ]
        scores.hallucination_rate = metrics.material_hallucination_rate(
            hall_scores, floor=int(FAILURE_THRESHOLD)
        )

    record.accuracy = round(scores.accuracy, 4)
    record.calibration_ece = round(scores.calibration, 4)
    record.groundedness = round(scores.groundedness, 4)
    record.actionability = round(scores.actionability, 4)
    record.failure_mode_recall = round(scores.failure_mode_recall, 4)
    record.hallucination_rate = round(scores.hallucination_rate, 4)
    record.weighted_total = round(scores.weighted_total(), 4)
    record.scenario_breakdown = _scenario_breakdown(results)

    if persist:
        save_run(record)
        calib_points = [
            CalibrationPoint(
                run_id=record.run_id,
                case_id=r.case_id,
                channel=rec.channel,
                confidence=rec.confidence,
                prob=rec.prob,
                correct=rec.correct,
                agent_rank=rec.agent_rank,
                true_rank=rec.true_rank,
            )
            for r in results
            for rec in r.calib_records
        ]
        save_calibration_points(calib_points)
    return record
