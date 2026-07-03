from app.agents.handlers.base import BaseHandler


class RecommendationHandler(BaseHandler):
    question_type = "recommendation"
    uses_knowledge_base = True

    def extra_grounding(self, session, message) -> str:
        return (
            "GUIDANCE: Produce a specific, executable action with a priority and "
            "explicit dependencies. Avoid vague advice like 'consider testing'."
        )
