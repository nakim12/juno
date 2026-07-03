from app.agents.handlers.base import BaseHandler


class InterpretationHandler(BaseHandler):
    question_type = "interpretation"
    uses_knowledge_base = True
