from app.agents.handlers.base import BaseHandler


class UncertaintyHandler(BaseHandler):
    question_type = "uncertainty"
    uses_knowledge_base = True

    def extra_grounding(self, session, message) -> str:
        return (
            "GUIDANCE: Ground confidence in the width of credible intervals, model "
            "diagnostics, and any detected structural issues. Be explicit about what "
            "would raise or lower confidence."
        )
