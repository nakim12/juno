# Architecture Notes

This is a working companion to the full design doc
([`../mmm-copilot-design-doc.md`](../mmm-copilot-design-doc.md)). It captures
implementation-level decisions as they are made.

## Request flows

### Initial analysis (`POST /api/analyze` or `POST /api/samples/{id}/load`)

1. `SessionStore.create` mints a session from the uploaded / sample `MMMOutput`.
2. `parsers.mmm_parser.parse` produces a deterministic `MMMSummary` and flags
   structural issues (wide CIs, high adstock, low contribution).
3. `rag.retriever.retrieve` fetches methodology context (no-op until Phase 2).
4. `agents.initial_analysis` calls the analysis agent for a structured
   `AnalysisReport`, or falls back to a deterministic report when no key is set.
5. The report is cached on the session and returned.
6. `GET /api/analyze/{session_id}/stream` replays the report as SSE sections.

### Chat (`POST /api/chat`, SSE)

1. `agents.chat_router.classify` labels the question (LLM, keyword fallback).
2. The matching handler in `agents/handlers/` builds grounding (report + raw
   output + recent turns + optional KB) and streams tokens back.
3. The turn is appended to session history.

## Key design principles (design doc §4.2)

- Separation of parsed representation (`MMMSummary`) from natural-language
  interpretation (`AnalysisReport`) so each layer is independently testable.
- Explicit uncertainty as a first-class output on every channel and rec.
- RAG grounds *methodology*, never the numeric values.
- Session-scoped memory only; no cross-session state.
- Streaming everywhere via SSE.

## Deferred / open

- BlueAlpha simulator interface (`evaluation/benchmark_generator.py`).
- Cross-encoder rerank in `rag/retriever.py`.
- Anthropic structured-output / tools API (currently prompt-level JSON schema).
