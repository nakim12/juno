from app.agents.handlers.base import BaseHandler


class HypotheticalHandler(BaseHandler):
    question_type = "hypothetical"
    uses_knowledge_base = True

    def extra_grounding(self, session, message) -> str:
        # A future version can attach a saturation/adstock calculation tool here.
        return (
            "GUIDANCE: Reason about the counterfactual using the channel's "
            "saturation and adstock parameters. Flag when the scenario extrapolates "
            "beyond the observed spend range."
        )
