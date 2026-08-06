"""Judge validation (design doc 9.2).

Before trusting the LLM-as-judge, we validate it two ways:

1. **Reliability (test-retest)**: re-run the judge K times on the *same* agent
   outputs and measure self-consistency per dimension. A judge that returns
   wildly different scores on reruns is noise, not signal. Fully automatable.

2. **Validity (agreement with a human)**: compare judge scores against
   hand-labelled reference scores using Cohen's kappa. This needs human labels,
   so we generate a labelling template pre-filled with the judge's own scores
   for the reviewer to complete, then compute agreement once it is filled in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.llm import LLMClient, get_judge_llm
from app.evaluation import metrics
from app.evaluation.benchmark_generator import BENCHMARKS_DIR, BenchmarkCase
from app.evaluation.judge import judge_response
from app.evaluation.reference import get_references
from app.evaluation.reports_cache import get_reports
from app.models.analysis_report import AnalysisReport

_DIMENSIONS = [
    "accuracy",
    "calibration",
    "groundedness",
    "actionability",
    "failure_mode_detection",
    "hallucination",
]


@dataclass
class ReliabilityResult:
    n_cases: int
    k_repetitions: int
    per_dimension: dict[str, dict[str, float]]  # dim -> {mean_std, exact_match, kappa}
    overall_kappa: float


async def _judge_once(
    case: BenchmarkCase, report: AnalysisReport, reference: str, llm: LLMClient
) -> dict[str, int]:
    verdict = await judge_response(
        ground_truth=str(case.ground_truth),
        reference=reference,
        agent_response=report.model_dump_json(),
        llm=llm,
    )
    return {d.dimension: d.score for d in verdict.scores}


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


async def measure_reliability(
    cases: list[BenchmarkCase],
    version: str = "v1",
    k: int = 3,
    use_llm_agent: bool = True,
    llm: LLMClient | None = None,
) -> ReliabilityResult:
    """Judge each case's report ``k`` times and quantify self-consistency."""
    llm = llm or get_judge_llm()
    reports = await get_reports(cases, version=version, use_llm=use_llm_agent)
    references = await get_references(cases, version=version, llm=llm)

    # scores_by_dim[dim] = list of per-case score lists across reps
    scores_by_dim: dict[str, list[list[int]]] = {d: [] for d in _DIMENSIONS}
    for case in cases:
        report = reports.get(case.case_id)
        if report is None:
            continue
        reps = [
            await _judge_once(case, report, references.get(case.case_id, ""), llm)
            for _ in range(k)
        ]
        for dim in _DIMENSIONS:
            per_rep = [r.get(dim) for r in reps if dim in r]
            if len(per_rep) == k:
                scores_by_dim[dim].append(per_rep)

    per_dimension: dict[str, dict[str, float]] = {}
    all_first: list[int] = []
    all_second: list[int] = []
    for dim, case_reps in scores_by_dim.items():
        if not case_reps:
            continue
        # Test-retest between the first two repetitions.
        first = [reps[0] for reps in case_reps]
        second = [reps[1] for reps in case_reps] if k >= 2 else first
        all_first.extend(first)
        all_second.extend(second)
        mean_std = sum(_std([float(x) for x in reps]) for reps in case_reps) / len(case_reps)
        exact = sum(1 for reps in case_reps if len(set(reps)) == 1) / len(case_reps)
        per_dimension[dim] = {
            "mean_std": round(mean_std, 4),
            "all_identical_rate": round(exact, 4),
            "test_retest_kappa": metrics.cohens_kappa(first, second),
        }

    overall_kappa = metrics.cohens_kappa(all_first, all_second) if all_first else 0.0
    return ReliabilityResult(
        n_cases=len(cases),
        k_repetitions=k,
        per_dimension=per_dimension,
        overall_kappa=round(overall_kappa, 4),
    )


# --------------------------------------------------------------------------- #
# Validity: agreement with human labels
# --------------------------------------------------------------------------- #

def _labels_path(version: str) -> Path:
    return BENCHMARKS_DIR / f"human_labels_{version}.json"


async def write_labeling_template(
    cases: list[BenchmarkCase],
    version: str = "v1",
    use_llm_agent: bool = True,
    llm: LLMClient | None = None,
) -> Path:
    """Write a template pre-filled with the judge's scores for a human to complete.

    Each entry has the agent's overview, the judge's score per dimension, and a
    ``human_score`` slot (``null``) for the reviewer to fill with a 0-5 integer.
    """
    llm = llm or get_judge_llm()
    reports = await get_reports(cases, version=version, use_llm=use_llm_agent)
    references = await get_references(cases, version=version, llm=llm)

    entries = []
    for case in cases:
        report = reports.get(case.case_id)
        if report is None:
            continue
        judge_scores = await _judge_once(
            case, report, references.get(case.case_id, ""), llm
        )
        entries.append(
            {
                "case_id": case.case_id,
                "agent_overview": report.overview,
                "known_failure_modes": case.ground_truth.known_failure_modes,
                "scores": {
                    dim: {"judge_score": judge_scores.get(dim), "human_score": None}
                    for dim in _DIMENSIONS
                },
            }
        )

    path = _labels_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return path


def compute_validity(version: str = "v1") -> dict[str, dict[str, float]]:
    """Compute judge-vs-human agreement from a completed labels file.

    Returns per-dimension agreement stats (exact match, within-one, kappa, MAE)
    plus an ``overall`` aggregate. Raises if the labels file is missing or has no
    completed ``human_score`` values.
    """
    path = _labels_path(version)
    if not path.exists():
        raise FileNotFoundError(
            f"No labels file at {path}. Generate one with the --template command "
            "and fill in the human_score values first."
        )
    entries = json.loads(path.read_text(encoding="utf-8"))

    judge_by_dim: dict[str, list[int]] = {d: [] for d in _DIMENSIONS}
    human_by_dim: dict[str, list[int]] = {d: [] for d in _DIMENSIONS}
    for entry in entries:
        for dim, pair in entry.get("scores", {}).items():
            j, h = pair.get("judge_score"), pair.get("human_score")
            if j is not None and h is not None:
                judge_by_dim[dim].append(int(j))
                human_by_dim[dim].append(int(h))

    result: dict[str, dict[str, float]] = {}
    all_j: list[int] = []
    all_h: list[int] = []
    for dim in _DIMENSIONS:
        if judge_by_dim[dim]:
            result[dim] = metrics.agreement_report(judge_by_dim[dim], human_by_dim[dim])
            all_j.extend(judge_by_dim[dim])
            all_h.extend(human_by_dim[dim])
    if not all_j:
        raise ValueError(
            "No completed human_score values found. Fill in the labels file first."
        )
    result["overall"] = metrics.agreement_report(all_j, all_h)
    return result
