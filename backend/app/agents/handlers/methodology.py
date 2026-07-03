from app.agents.handlers.base import BaseHandler


class MethodologyHandler(BaseHandler):
    question_type = "methodology"
    uses_knowledge_base = True
