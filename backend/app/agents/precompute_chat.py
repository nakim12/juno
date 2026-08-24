"""Pre-compute chat answers for the bundled samples.

Run once by the project owner, with a funded key:

    python -m app.agents.precompute_chat            # all samples
    python -m app.agents.precompute_chat --sample three_channel_small_budget

Each question goes through the real pipeline — router, handler, retrieval — so
the cached answer is genuinely what the agent said, not a hand-written script.
The result is committed, letting the public demo serve the full chat experience
without an API key.

Questions are chosen to spread across router types and to land on the parts of
each scenario worth talking about (a wide credible interval, a saturating
channel, a high-ROI channel that's too small to matter).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.agents import chat_cache, chat_router, sample_cache
from app.models.mmm_output import MMMOutput
from app.parsers import mmm_parser
from app.session.store import Session, session_store

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"

CURATED: dict[str, list[str]] = {
    "six_channel_with_saturation": [
        "Which channel is actually delivering the best return?",
        "How much should I trust the TikTok number?",
        "Where should I move budget next quarter?",
        "What if I doubled Search spend?",
        "What does saturation mean for my budget decisions?",
        "Is Affiliate really better than Search?",
    ],
    "three_channel_small_budget": [
        "What's the headline read on this model?",
        "Should I cut Display?",
        "Is the Social result reliable enough to act on?",
        "Why are the credible intervals so wide?",
        "What if I moved Display budget into Search?",
    ],
}


def _session_for(sample_id: str) -> Session:
    path = SAMPLES_DIR / f"{sample_id}.json"
    mmm = MMMOutput.model_validate_json(path.read_text(encoding="utf-8"))
    session = session_store.create(mmm)
    session.summary = mmm_parser.parse(mmm)

    report = sample_cache.get(sample_id, allow_stale=True)
    if report is None:
        raise SystemExit(
            f"No cached analysis for '{sample_id}'. Load it once via the API "
            "so the report cache is populated, then re-run this."
        )
    session.report = report
    return session


async def _answer(session: Session, question: str) -> chat_cache.CachedAnswer:
    # Ask each question against a clean history: a visitor clicking a suggestion
    # sees a standalone answer, not one shaped by the previous exchange.
    session.history.clear()

    question_type, chunks, token_stream = await chat_router.route_and_stream(
        session, question
    )
    text = "".join([token async for token in token_stream])

    # Mirrors the SSE payload built in app/api/chat.py so the replay is identical.
    sources = [
        {
            "chunk_id": c.chunk_id,
            "topic": c.topic,
            "source": c.source,
            "snippet": (c.text[:220] + "…") if len(c.text) > 220 else c.text,
        }
        for c in chunks
    ]
    return chat_cache.CachedAnswer(
        question=question,
        question_type=question_type,
        answer=text,
        sources=sources,
    )


async def run(sample_ids: list[str]) -> None:
    for sample_id in sample_ids:
        questions = CURATED.get(sample_id)
        if not questions:
            print(f"! no curated questions for '{sample_id}', skipping")
            continue

        session = _session_for(sample_id)
        answers: list[chat_cache.CachedAnswer] = []
        for i, question in enumerate(questions, 1):
            print(f"[{sample_id}] {i}/{len(questions)} {question}")
            answer = await _answer(session, question)
            print(f"    -> {answer.question_type}, {len(answer.answer)} chars, "
                  f"{len(answer.sources)} sources")
            answers.append(answer)

        path = chat_cache.save(sample_id, answers)
        print(f"Wrote {len(answers)} answers to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        action="append",
        dest="samples",
        help="Sample id to pre-compute (repeatable). Defaults to all curated samples.",
    )
    parser.add_argument(
        "--list", action="store_true", help="Print the curated questions and exit."
    )
    args = parser.parse_args()

    if args.list:
        print(json.dumps(CURATED, indent=2))
        return

    asyncio.run(run(args.samples or list(CURATED)))


if __name__ == "__main__":
    main()
