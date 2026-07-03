from app.agents.handlers.base import BaseHandler


class ComparisonHandler(BaseHandler):
    question_type = "comparison"
    uses_knowledge_base = False

    def extra_grounding(self, session, message) -> str:
        return (
            "GUIDANCE: Compare channels on ROI point estimate AND interval overlap. "
            "If credible intervals overlap heavily, say the ranking is not reliable."
        )
