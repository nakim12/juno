"""Bring-your-own-key support.

A visitor can unlock live generation by supplying their own Anthropic key on the
request. This keeps the public demo free to run — the server's own key is never
spent on visitor traffic when `demo_mode` is on — while still letting anyone who
wants to see the real agent do so at their own expense.

The key is read from a header, used for the lifetime of the request, and never
logged or persisted. Nothing here writes it to disk, the session store, or the
evaluation database.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header

from app.core.config import settings
from app.core.llm import LLMClient

CALLER_KEY_HEADER = "X-Anthropic-Api-Key"

# Anthropic keys start with this; a cheap sanity check so an obviously wrong
# value fails here rather than as a confusing 401 mid-stream.
_KEY_PREFIX = "sk-ant-"


@dataclass(frozen=True)
class LLMAccess:
    """How (and whether) the current request is allowed to call the LLM.

    ``billed_to_server`` is what the rate limiter cares about: a caller spending
    their own credit doesn't need protecting from, and shouldn't be throttled by,
    our budget guards.
    """

    key: str | None
    billed_to_server: bool

    @property
    def can_generate(self) -> bool:
        return bool(self.key)

    def agent_llm(self) -> LLMClient:
        return LLMClient(api_key=self.key, model=settings.agent_model)


def resolve_llm_access(caller_key: str | None) -> LLMAccess:
    """Decide which key, if any, this request may use.

    A caller-supplied key always wins. Otherwise the server key is offered only
    when demo mode is off — that's the switch that keeps public traffic from
    billing the owner.
    """
    if caller_key and caller_key.strip().startswith(_KEY_PREFIX):
        return LLMAccess(key=caller_key.strip(), billed_to_server=False)

    if settings.demo_mode:
        return LLMAccess(key=None, billed_to_server=False)

    server_key = settings.anthropic_api_key or None
    return LLMAccess(key=server_key, billed_to_server=bool(server_key))


async def llm_access(
    x_anthropic_api_key: str | None = Header(default=None),
) -> LLMAccess:
    """FastAPI dependency exposing :func:`resolve_llm_access` to routes."""
    return resolve_llm_access(x_anthropic_api_key)
