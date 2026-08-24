"""Registry mapping question types to their handlers (design doc 5.2)."""

from __future__ import annotations

from app.agents.handlers.base import BaseHandler
from app.agents.handlers.clarification import ClarificationHandler
from app.agents.handlers.comparison import ComparisonHandler
from app.agents.handlers.hypothetical import HypotheticalHandler
from app.agents.handlers.interpretation import InterpretationHandler
from app.agents.handlers.methodology import MethodologyHandler
from app.agents.handlers.recommendation import RecommendationHandler
from app.agents.handlers.uncertainty import UncertaintyHandler
from app.core.llm import LLMClient
from app.models.chat_message import QuestionType

_HANDLERS: dict[QuestionType, type[BaseHandler]] = {
    "interpretation": InterpretationHandler,
    "recommendation": RecommendationHandler,
    "methodology": MethodologyHandler,
    "hypothetical": HypotheticalHandler,
    "comparison": ComparisonHandler,
    "uncertainty": UncertaintyHandler,
    "clarification": ClarificationHandler,
}


def get_handler(
    question_type: QuestionType, llm: LLMClient | None = None
) -> BaseHandler:
    handler_cls = _HANDLERS.get(question_type, InterpretationHandler)
    return handler_cls(llm)


__all__ = ["get_handler", "BaseHandler"]
