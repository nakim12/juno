"""Reference interpretation generation (design doc 5.4).

For each benchmark case we generate an *ideal* interpretation with a stronger
model (the judge model, Opus) that has access to the ground truth. The judge
then scores the agent's response against this reference. References are cached to
disk so they are generated once per benchmark version and reused across runs
(design doc R1: cache aggressively to control API cost).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.llm import LLMClient, LLMNotConfigured, get_judge_llm
from app.evaluation.benchmark_generator import BENCHMARKS_DIR, BenchmarkCase

REFERENCE_SYSTEM = """You are a senior marketing-science analyst writing a GOLD
STANDARD interpretation of a Marketing Mix Model output. You have privileged
access to the ground-truth parameters that generated this scenario. Write the
interpretation a perfect analyst would produce: rank channels by true ROI, call
out the known structural risks explicitly, give a specific budget recommendation,
and state calibrated confidence. Be concise (250-400 words). This text is used as
the reference answer when grading another model, so it must be correct and
well-grounded in the ground truth provided.
"""


def _reference_path(version: str) -> Path:
    return BENCHMARKS_DIR / f"references_{version}.json"


def _build_user_prompt(case: BenchmarkCase) -> str:
    gt = case.ground_truth
    return (
        f"GROUND_TRUTH:\n"
        f"- true_roi (by channel): {json.dumps(gt.true_roi)}\n"
        f"- true_half_saturation: {json.dumps(gt.true_half_saturation)}\n"
        f"- true_adstock: {json.dumps(gt.true_adstock)}\n"
        f"- optimal_allocation: {json.dumps(gt.optimal_allocation)}\n"
        f"- known_failure_modes: {gt.known_failure_modes}\n\n"
        f"REPORTED_MMM_OUTPUT:\n{case.mmm_output.model_dump_json(indent=2)}\n\n"
        "Write the gold-standard interpretation."
    )


async def generate_reference(case: BenchmarkCase, llm: LLMClient | None = None) -> str:
    llm = llm or get_judge_llm()
    return await llm.complete(
        REFERENCE_SYSTEM, _build_user_prompt(case), max_tokens=1024
    )


def _fallback_reference(case: BenchmarkCase) -> str:
    gt = case.ground_truth
    return (
        "REFERENCE (deterministic fallback, no judge LLM configured). "
        f"True ROI ranking: {gt.true_ranking()}. "
        f"Known failure modes: {gt.known_failure_modes}. "
        f"Optimal allocation: {json.dumps(gt.optimal_allocation)}."
    )


async def get_references(
    cases: list[BenchmarkCase],
    version: str = "v1",
    llm: LLMClient | None = None,
    *,
    concurrency: int = 4,
) -> dict[str, str]:
    """Return {case_id: reference}, generating and caching any that are missing.

    Missing references are generated up to ``concurrency`` at a time. Falls back
    to a deterministic ground-truth summary string when no judge LLM is
    configured, so the harness remains runnable without an API key.
    """
    path = _reference_path(version)
    cache: dict[str, str] = {}
    if path.exists():
        cache = json.loads(path.read_text(encoding="utf-8"))

    missing = [c for c in cases if c.case_id not in cache]
    if missing:
        llm = llm or get_judge_llm()
        sem = asyncio.Semaphore(max(1, concurrency))

        async def _one(case: BenchmarkCase) -> tuple[str, str]:
            async with sem:
                try:
                    return case.case_id, await generate_reference(case, llm)
                except LLMNotConfigured:
                    return case.case_id, _fallback_reference(case)

        for cid, ref in await asyncio.gather(*(_one(c) for c in missing)):
            cache[cid] = ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    return cache
