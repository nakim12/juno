"""Thin wrapper around the Anthropic client.

Centralizes model selection, structured-output parsing, and request logging so
that every LLM call in the system is consistent and auditable (design doc 5.6).
The Anthropic SDK is imported lazily so the app can boot without a key during
local scaffolding / tests.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMNotConfigured(RuntimeError):
    """Raised when an LLM call is attempted without an API key."""


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or settings.anthropic_api_key
        self._model = model or settings.agent_model
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if not self._api_key:
            raise LLMNotConfigured(
                "ANTHROPIC_API_KEY is not set. Add it to backend/.env to enable LLM calls."
            )
        if self._client is None:
            # Imported lazily to keep the dependency optional during scaffolding.
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> str:
        client = self._ensure_client()
        resp = await client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    async def stream(
        self, system: str, user: str, max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        client = self._ensure_client()
        async with client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def structured(
        self, system: str, user: str, schema: type[T], max_tokens: int = 2048
    ) -> T:
        """Request JSON matching ``schema`` and validate it.

        Uses prompt-level JSON-schema enforcement. Swap for the Anthropic tools /
        structured-output API as it stabilizes.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        augmented_system = (
            f"{system}\n\nRespond with ONLY a JSON object matching this schema:\n"
            f"{schema_json}\nDo not include markdown fences or prose."
        )
        raw = await self.complete(augmented_system, user, max_tokens=max_tokens)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return schema.model_validate_json(raw)


def get_agent_llm() -> LLMClient:
    return LLMClient(model=settings.agent_model)


def get_judge_llm() -> LLMClient:
    return LLMClient(model=settings.judge_model)
