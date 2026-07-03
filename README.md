# Juno

**Juno is an agentic AI copilot that turns Marketing Mix Model (MMM) outputs into
trustworthy, grounded business decisions — backed by a rigorous evaluation
framework that quantifies whether the agent's advice can be trusted.**

The project has two pieces of equal weight:

1. **The tool** — a multi-agent chat system that interprets MMM outputs,
   generates recommendations, and answers marketer questions with grounded
   reasoning and explicit confidence.
2. **The evaluation framework** — a benchmark suite that stress-tests the agent
   against ground-truth MMM outputs, using LLM-as-judge to quantify accuracy,
   calibration, groundedness, and hallucination rate.

See [`mmm-copilot-design-doc.md`](./mmm-copilot-design-doc.md) for the full design.

---

## Repository layout

```
juno/
├── backend/          FastAPI service (agents, RAG, parser, evaluation, session)
│   ├── app/
│   │   ├── api/          REST + SSE endpoints
│   │   ├── agents/       initial-analysis pipeline, chat router, handlers, prompts
│   │   ├── parsers/      deterministic MMM parsing
│   │   ├── rag/          Chroma retrieval + corpus indexing
│   │   ├── evaluation/   benchmark runner, LLM-as-judge, metrics, failure catalog
│   │   ├── models/       Pydantic schemas
│   │   ├── session/      in-memory session store (Redis-ready)
│   │   └── core/         config + LLM client
│   ├── data/samples/     bundled sample MMM outputs
│   └── tests/
├── frontend/         Next.js 14 (App Router) + TypeScript + Tailwind
├── dashboard/        Streamlit eval-metrics dashboard
├── evaluation/       benchmark sets + eval docs
└── docs/
```

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind |
| Backend | FastAPI, Python 3.11+ |
| LLM (agent) | Claude Sonnet 4.5 |
| LLM (judge) | Claude Opus 4.5 |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector DB | Chroma |
| Eval DB | SQLite |
| Eval dashboard | Streamlit |

## Quickstart

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY (optional for the skeleton)
uvicorn app.main:app --reload --port 8000
```

Without an API key, the analysis pipeline falls back to a deterministic report
and chat returns a configuration notice — so the end-to-end skeleton is
demoable before any keys are wired.

Run the tests:

```bash
cd backend && source .venv/bin/activate && pytest -q
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # BACKEND_URL defaults to http://localhost:8000
npm run dev                   # http://localhost:3000
```

### Knowledge base (RAG)

Drop methodology documents into `backend/app/rag/corpus/`, then:

```bash
cd backend && source .venv/bin/activate
python -m app.rag.indexer --reset
```

### Eval dashboard

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

## Deployment

Frontend deploys to **Vercel**, backend to **Render** (a `render.yaml` blueprint
and a `backend/Dockerfile` are included). See
[`docs/deployment.md`](./docs/deployment.md) for step-by-step instructions.

## Build phases

Development follows the phased plan in the design doc (§8):

1. **Foundation** — end-to-end skeleton (this scaffold) ← *you are here*
2. **RAG + knowledge base** — retrieval-grounded responses with citations
3. **Multi-agent architecture** — router + specialized handlers, structured output
4. **Evaluation framework** — benchmarks, LLM-as-judge, metrics, failure catalog
5. **Polish + writeup**
6. **Iteration**

## Status

Phase 1 scaffold: project structure, typed schemas, deterministic parser, agent
pipeline with LLM + heuristic fallback, router + handlers, SSE streaming
endpoints, sample loader, and a Next.js UI. RAG and the eval harness have working
interfaces with stubs to be filled in during Phases 2 and 4.
