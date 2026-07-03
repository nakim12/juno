"""LLM-as-judge harness (design doc 5.4, 9.2).

The judge uses a different model from the agent (Opus vs Sonnet) to reduce
same-model bias, and scores each response on the six design-doc dimensions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.llm import LLMClient, get_judge_llm

Score = int  # 0-5

JUDGE_SYSTEM = """You are an impartial evaluator of an MMM analysis assistant.
Given the ground-truth MMM scenario, a reference interpretation, and the agent's
response, score the agent on each dimension from 0 (poor) to 5 (excellent).
Be strict: reward grounded, calibrated, actionable answers and penalize
hallucination and overconfidence. Provide brief reasoning per dimension.
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
