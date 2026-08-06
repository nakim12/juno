"""LLM-as-judge harness (design doc 5.4, 9.2).

The judge uses a different model from the agent (Opus vs Sonnet) to reduce
same-model bias, and scores each response on the six design-doc dimensions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.llm import LLMClient, get_judge_llm

Score = int  # 0-5

JUDGE_SYSTEM = """You are an impartial evaluator of an MMM (Marketing Mix Modeling)
analysis assistant. You are given the ground-truth scenario, a reference
interpretation, and the agent's response. Score each dimension from 0 (poor) to
5 (excellent) and give one sentence of reasoning. Judge ONLY against the
GROUND_TRUTH and REFERENCE — never against outside assumptions.

Dimension rubrics (anchor your score to these):

- accuracy: does the channel ranking and the quantitative reads match ground truth?
  5 = ranking and magnitudes match; 3 = ranking mostly right, minor errors; 0 = wrong.

- calibration: does stated confidence track how correct each claim actually is?
  5 = confident when right, hedged when uncertain; 0 = confident-and-wrong, or hedges everything.

- groundedness: is every claim traceable to the model output or a cited methodology source?
  5 = all claims grounded, citations valid; 3 = mostly grounded, a citation weak/missing; 0 = ungrounded.

- actionability: are recommendations specific, prioritized, and decision-ready?
  5 = concrete, prioritized, with dependencies; 3 = generic but usable; 0 = vague or absent.

- failure_mode_detection: did the agent surface the scenario's known risks
  (wide CI, saturation, multicollinearity, low contribution, high adstock)?
  5 = all present risks flagged; 3 = some; 0 = missed obvious risks.

- hallucination: does the response state anything NOT supported by the model output
  or reference? This dimension measures FABRICATION, not imperfection. Anchor strictly:
    5 = no unsupported content; every number and named entity traces to the input.
    4 = no fabrication; only slightly loose wording of an otherwise supported fact.
    3 = one unsupported *qualitative* generalization, but no invented numbers or entities.
    2 = contains an invented number, channel, or claim absent from the input (a MATERIAL hallucination).
    1 = several fabricated claims.
    0 = largely fabricated.
  Do NOT lower this score for being terse, generic, or imperfect — only for
  unsupported or invented content. A correct, well-grounded answer scores 5 here
  even if it is brief.
"""


class DimensionScore(BaseModel):
    dimension: Literal[
        "accuracy",
        "calibration",
        "groundedness",
        "actionability",
        "failure_mode_detection",
        "hallucination",
    ]
    score: Score = Field(..., ge=0, le=5)
    reasoning: str


class JudgeVerdict(BaseModel):
    scores: list[DimensionScore]
    overall_reasoning: str


async def judge_response(
    ground_truth: str,
    reference: str,
    agent_response: str,
    llm: LLMClient | None = None,
) -> JudgeVerdict:
    llm = llm or get_judge_llm()
    user = (
        f"GROUND_TRUTH:\n{ground_truth}\n\n"
        f"REFERENCE_INTERPRETATION:\n{reference}\n\n"
        f"AGENT_RESPONSE:\n{agent_response}"
    )
    return await llm.structured(JUDGE_SYSTEM, user, JudgeVerdict, max_tokens=2048)
