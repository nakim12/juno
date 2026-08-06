"""Thin wrapper around the Anthropic client.

Centralizes model selection, structured-output parsing, and request logging so
that every LLM call in the system is consistent and auditable (design doc 5.6).
The Anthropic SDK is imported lazily so the app can boot without a key during
local scaffolding / tests.
"""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

# HTTP statuses worth retrying: rate limits (429), transient server errors, and
# Anthropic's "overloaded" (529). Anything else fails fast.
_RETRYABLE_STATUSES = {429, 500, 502, 503, 529}


class LLMNotConfigured(RuntimeError):
    """Raised when an LLM call is attempted without an API key."""


async def _with_retries(fn: Callable[[], Awaitable[T]], *, tries: int = 5) -> T:
    """Call ``fn`` with exponential backoff on rate-limit / transient errors.

    This keeps concurrent eval runs from wasting spend when the account's
    rate/token-per-minute limits kick in — the request is retried rather than
    recorded as a failed case.
    """
    delay = 2.0
    for attempt in range(tries):
        try:
            return await fn()
        except LLMNotConfigured:
            raise
        except Exception as exc:  # noqa: BLE001 — inspect then re-raise if fatal
            status = getattr(exc, "status_code", None)
            msg = str(exc).lower()
            retryable = status in _RETRYABLE_STATUSES or any(
                s in msg for s in ("rate limit", "overloaded", "timeout", "529", "429")
            )
            if not retryable or attempt == tries - 1:
                raise
            await asyncio.sleep(delay + random.random())
            delay = min(delay * 2, 30.0)
    raise RuntimeError("unreachable")  # pragma: no cover


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        # Distinguish "not provided" (None -> use settings) from an explicit empty
        # string (force the unconfigured path, used by the eval harness's LLM-free
        # mode). ``"" or settings...`` would incorrectly fall back to the real key.
        self._api_key = settings.anthropic_api_key if api_key is None else api_key
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

        async def _call() -> Any:
            return await client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )

        resp = await _with_retries(_call)
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

    @staticmethod
    def _schema_system(system: str, schema: type[BaseModel]) -> str:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        return (
            f"{system}\n\nRespond with ONLY a JSON object matching this schema:\n"
            f"{schema_json}\nDo not include markdown fences or prose."
        )

    @staticmethod
    def _parse_json(raw: str, schema: type[T]) -> T:
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return schema.model_validate_json(raw)

    async def structured(
        self, system: str, user: str, schema: type[T], max_tokens: int = 2048
    ) -> T:
        """Request JSON matching ``schema`` and validate it.

        Uses prompt-level JSON-schema enforcement. Swap for the Anthropic tools /
        structured-output API as it stabilizes.
        """
        raw = await self.complete(
            self._schema_system(system, schema), user, max_tokens=max_tokens
        )
        return self._parse_json(raw, schema)

    async def structured_stream(
        self, system: str, user: str, schema: type[BaseModel], max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """Stream the raw JSON tokens for a structured request as they generate.

        Callers accumulate the yielded text and parse it with
        :meth:`_parse_json` once the stream completes.
        """
        async for text in self.stream(
            self._schema_system(system, schema), user, max_tokens=max_tokens
        ):
            yield text


def get_agent_llm() -> LLMClient:
    return LLMClient(model=settings.agent_model)


def get_judge_llm() -> LLMClient:
    return LLMClient(model=settings.judge_model)
