"""Benchmark runner (design doc 5.4, 7.3).

Iterates benchmark cases through the agent, scores them with the judge, logs
failures, and aggregates metrics. Runs offline / batch.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents import initial_analysis
from app.evaluation.benchmark_generator import BenchmarkCase
from app.evaluation.failure_catalog import FailureEntry, log_failure
from app.evaluation.judge import judge_response
from app.evaluation.metrics import DimensionScores, spearman_rank_correlation

FAILURE_THRESHOLD = 3.0  # judge dimensions below this get catalogued


@dataclass
class CaseResult:
    case_id: str
    agent_ranking: list[str]
    truth_ranking: list[str]
    accuracy: float


async def run_case(case: BenchmarkCase) -> CaseResult:
    summary, report = await initial_analysis.run(case.mmm_output, session_id=case.case_id)
    agent_ranking = summary.ranked_channels()
    truth_ranking = [
        name for name, _ in sorted(
            case.ground_truth.true_roi.items(), key=lambda kv: kv[1], reverse=True
        )
    ]
    accuracy = spearman_rank_correlation(agent_ranking, truth_ranking)

    verdict = await judge_response(
        ground_truth=str(case.ground_truth),
        reference=report.overview,
        agent_response=report.model_dump_json(),
    )
    for dim in verdict.scores:
        if dim.score < FAILURE_THRESHOLD:
            log_failure(
                FailureEntry(
                    case_id=case.case_id,
                    category=dim.dimension,
                    agent_response=report.overview,
                    judge_reasoning=dim.reasoning,
                    score=float(dim.score),
                )
            )
    return CaseResult(
        case_id=case.case_id,
        agent_ranking=agent_ranking,
        truth_ranking=truth_ranking,
        accuracy=accuracy,
    )


async def run_suite(cases: list[BenchmarkCase]) -> DimensionScores:
    results = [await run_case(c) for c in cases]
    mean_accuracy = sum(r.accuracy for r in results) / len(results) if results else 0.0
    return DimensionScores(accuracy=mean_accuracy)
