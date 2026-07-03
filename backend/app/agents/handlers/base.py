"""Base class for chat question handlers (design doc 5.2).

Each handler follows the same template: gather grounding from the cached report,
raw output, recent conversation, and (optionally) the knowledge base; build a
prompt; stream the answer. Subclasses override :meth:`extra_grounding` and
:attr:`uses_knowledge_base` to specialize retrieval per question type.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.agents import prompts
from app.core.llm import LLMClient, get_agent_llm
from app.models.chat_message import QuestionType
from app.rag.retriever import retriever
from app.session.store import Session

PROMPT_NAME = "chat"
HISTORY_TURNS = 3


class BaseHandler:
    question_type: QuestionType
    uses_knowledge_base: bool = False

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or get_agent_llm()

    def extra_grounding(self, session: Session, message: str) -> str:
        """Hook for subclasses to add question-type-specific grounding."""
        return ""

    def _knowledge_base(self, message: str) -> str:
        if not self.uses_knowledge_base:
            return ""
        chunks = retriever.retrieve(message)
        if not chunks:
            return ""
        return "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in chunks)

    def _build_user_prompt(self, session: Session, message: str) -> str:
        report_json = (
            session.report.model_dump_json(indent=2) if session.report else "(no report)"
        )
        recent = session.history[-HISTORY_TURNS * 2 :]
        convo = "\n".join(f"{m.role}: {m.content}" for m in recent) or "(none)"
        parts = [
            f"ANALYSIS_REPORT:\n{report_json}",
            f"MMM_OUTPUT:\n{session.mmm_output.model_dump_json(indent=2)}",
            f"CONVERSATION (recent):\n{convo}",
        ]
        kb = self._knowledge_base(message)
        if kb:
            parts.append(f"KNOWLEDGE_BASE:\n{kb}")
        extra = self.extra_grounding(session, message)
        if extra:
            parts.append(extra)
        parts.append(f"USER_QUESTION:\n{message}")
        return "\n\n".join(parts)

    async def stream(self, session: Session, message: str) -> AsyncIterator[str]:
        system = prompts.load(PROMPT_NAME).replace("{question_type}", self.question_type)
        user = self._build_user_prompt(session, message)
        async for token in self.llm.stream(system, user):
            yield token
