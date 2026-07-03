"""Chat router: classifies a question then delegates to a handler (design doc 5.2)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.agents import prompts
from app.agents.handlers import get_handler
from app.core.llm import LLMClient, LLMNotConfigured, get_agent_llm
from app.models.chat_message import QuestionType, RouterDecision
from app.session.store import Session

PROMPT_NAME = "router"

# Cheap keyword fallback used when no LLM key is configured.
_KEYWORDS: list[tuple[QuestionType, tuple[str, ...]]] = [
    ("recommendation", ("should i", "recommend", "what do i do", "budget")),
    ("hypothetical", ("what if", "if i", "suppose", "scenario")),
    ("comparison", ("better than", "compare", "versus", " vs ")),
    ("uncertainty", ("confident", "confidence", "trust", "reliable", "sure")),
    ("methodology", ("how does", "what is adstock", "saturation mean", "methodology")),
    ("clarification", ("you said", "don't understand", "didn't understand", "clarify")),
]


def _keyword_route(message: str) -> RouterDecision:
    lowered = f" {message.lower()} "
    for qtype, keywords in _KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return RouterDecision(question_type=qtype, reasoning="keyword-fallback")
    return RouterDecision(question_type="interpretation", reasoning="default-fallback")


async def classify(message: str, llm: LLMClient | None = None) -> RouterDecision:
    llm = llm or get_agent_llm()
    try:
        system = prompts.load(PROMPT_NAME)
        return await llm.structured(system, message, RouterDecision, max_tokens=256)
    except LLMNotConfigured:
        return _keyword_route(message)


async def route_and_stream(
    session: Session, message: str
) -> tuple[QuestionType, AsyncIterator[str]]:
    decision = await classify(message)
    handler = get_handler(decision.question_type)
    return decision.question_type, handler.stream(session, message)
