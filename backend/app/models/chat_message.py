"""Chat message schemas (design doc 5.2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.analysis_report import Citation, Confidence

QuestionType = Literal[
    "interpretation",
    "recommendation",
    "methodology",
    "hypothetical",
    "comparison",
    "uncertainty",
    "clarification",
]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class RouterDecision(BaseModel):
    question_type: QuestionType
    reasoning: str


class ChatResponse(BaseModel):
    """Tripartite response: answer + grounding + confidence (design doc 5.2)."""

    answer: str
    question_type: QuestionType
    confidence: Confidence
    confidence_reasoning: str
    grounding: list[Citation] = Field(default_factory=list)
