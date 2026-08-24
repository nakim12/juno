"""Chat endpoint with SSE streaming (design doc 5.6, 7.2).

Three ways a message gets answered, in order of preference:

1. **Pre-computed** — the question is one of the curated set for a bundled
   sample, so the stored answer is replayed. Free, and identical to what the
   agent actually said when it was generated offline.
2. **Live on the caller's key** — the visitor supplied their own credentials.
3. **Live on the server's key** — only when demo mode is off.

Demo mode exists so a public deployment can offer the full experience without
the owner's API credit being spendable by strangers.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.agents import chat_cache, chat_router
from app.core.caller_key import CALLER_KEY_HEADER, LLMAccess, llm_access
from app.core.config import settings
from app.core.llm import LLMNotConfigured
from app.core.rate_limit import llm_rate_limit
from app.models.chat_message import ChatMessage, ChatRequest
from app.session.store import Session, session_store

router = APIRouter(prefix="/api", tags=["chat"])

# Pacing for replayed answers. Real generation streams at roughly this rate, and
# matching it keeps a cached answer from arriving as an instant wall of text.
_REPLAY_CHUNK_CHARS = 4
_REPLAY_DELAY_S = 0.012


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _cached_answer(session: Session, message: str) -> chat_cache.CachedAnswer | None:
    if session.sample_id is None:
        return None
    return chat_cache.find(session.sample_id, message)


def _replay(session: Session, answer: chat_cache.CachedAnswer) -> StreamingResponse:
    """Stream a stored answer using the same events as a live response."""

    async def event_gen():
        yield _sse("meta", {"question_type": answer.question_type, "cached": True})
        if answer.sources:
            yield _sse("sources", {"sources": answer.sources})

        text = answer.answer
        for i in range(0, len(text), _REPLAY_CHUNK_CHARS):
            yield _sse("token", {"text": text[i : i + _REPLAY_CHUNK_CHARS]})
            await asyncio.sleep(_REPLAY_DELAY_S)

        session.history.append(ChatMessage(role="assistant", content=text))
        yield _sse("done", {})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def _provider_error_message(exc: Exception, caller_supplied: bool) -> str:
    """Turn a provider failure into something the person reading it can act on."""
    status_code = getattr(exc, "status_code", None)
    text = str(exc).lower()

    if status_code in (401, 403) or "authentication" in text or "invalid x-api-key" in text:
        return (
            "That API key was rejected by Anthropic. Check it's correct and active."
            if caller_supplied
            else "The server's API key was rejected."
        )
    if status_code == 429 or "rate limit" in text:
        return "Anthropic rate-limited this request. Wait a moment and try again."
    if "credit" in text or "billing" in text or status_code == 402:
        return (
            "That key has no available credit."
            if caller_supplied
            else "This demo's API credit is exhausted."
        )
    return "The model provider failed to respond. Try again in a moment."


def _live(session: Session, message: str, access: LLMAccess) -> StreamingResponse:
    async def event_gen():
        collected: list[str] = []
        caller_supplied = not access.billed_to_server

        try:
            question_type, chunks, token_stream = await chat_router.route_and_stream(
                session, message, llm=access.agent_llm()
            )
            yield _sse("meta", {"question_type": question_type, "cached": False})

            if chunks:
                sources = [
                    {
                        "chunk_id": c.chunk_id,
                        "topic": c.topic,
                        "source": c.source,
                        "snippet": (c.text[:220] + "…") if len(c.text) > 220 else c.text,
                    }
                    for c in chunks
                ]
                yield _sse("sources", {"sources": sources})

            async for token in token_stream:
                collected.append(token)
                yield _sse("token", {"text": token})

        except LLMNotConfigured:
            msg = (
                "Live chat isn't configured on this deployment. Try one of the "
                "suggested questions, or add your own Anthropic API key."
            )
            collected.append(msg)
            yield _sse("token", {"text": msg})
        except Exception as exc:  # noqa: BLE001 — surface, don't kill the stream
            # A bad key or a provider hiccup must not drop the connection
            # silently; that leaves the UI with an empty bubble and no reason.
            yield _sse("error", {"message": _provider_error_message(exc, caller_supplied)})

        if collected:
            session.history.append(
                ChatMessage(role="assistant", content="".join(collected))
            )
        yield _sse("done", {})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/chat/{session_id}/suggestions")
async def suggestions(session_id: str, access: LLMAccess = Depends(llm_access)) -> dict:
    """Questions this session can answer for free, plus what live mode requires."""
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    questions = (
        chat_cache.questions(session.sample_id) if session.sample_id else []
    )
    return {
        "questions": questions,
        # True when anything the visitor types will be answered live.
        "free_text_enabled": access.can_generate,
        "demo_mode": settings.demo_mode,
        "key_header": CALLER_KEY_HEADER,
    }


@router.post("/chat")
async def chat(
    req: ChatRequest, request: Request, access: LLMAccess = Depends(llm_access)
) -> StreamingResponse:
    session = session_store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    session.history.append(ChatMessage(role="user", content=req.message))

    # A stored answer is free and exact, so prefer it even in live mode.
    cached = _cached_answer(session, req.message)
    if cached is not None:
        return _replay(session, cached)

    if not access.can_generate:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "This is a free demo, so only the suggested questions are "
                "pre-answered. Add your own Anthropic API key to ask anything."
            ),
        )

    # Only guard spend that lands on the owner's key; a caller using their own
    # credentials is spending their own money.
    if access.billed_to_server:
        await llm_rate_limit(request)

    return _live(session, req.message, access)
