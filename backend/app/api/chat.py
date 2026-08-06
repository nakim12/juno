"""Chat endpoint with SSE streaming (design doc 5.6, 7.2)."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents import chat_router
from app.core.llm import LLMNotConfigured
from app.models.chat_message import ChatMessage, ChatRequest
from app.session.store import session_store

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    session = session_store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    session.history.append(ChatMessage(role="user", content=req.message))

    async def event_gen():
        question_type, chunks, token_stream = await chat_router.route_and_stream(
            session, req.message
        )
        yield f"event: meta\ndata: {json.dumps({'question_type': question_type})}\n\n"

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
            yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"

        collected: list[str] = []
        try:
            async for token in token_stream:
                collected.append(token)
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        except LLMNotConfigured:
            msg = (
                "LLM is not configured. Set ANTHROPIC_API_KEY in backend/.env to "
                "enable live chat responses."
            )
            collected.append(msg)
            yield f"event: token\ndata: {json.dumps({'text': msg})}\n\n"

        answer = "".join(collected)
        session.history.append(ChatMessage(role="assistant", content=answer))
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
