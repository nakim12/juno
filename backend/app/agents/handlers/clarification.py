from app.agents.handlers.base import BaseHandler


class ClarificationHandler(BaseHandler):
    question_type = "clarification"
    uses_knowledge_base = False

    def extra_grounding(self, session, message) -> str:
        return (
            "GUIDANCE: The user is asking about your previous response. Re-explain "
            "the relevant point more simply; do not introduce new claims."
        )
