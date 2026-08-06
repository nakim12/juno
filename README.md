# Juno

**Juno is an agentic AI copilot that turns Marketing Mix Model (MMM) outputs into
trustworthy, grounded business decisions — backed by a rigorous evaluation
framework that quantifies whether the agent's advice can actually be trusted.**

The project has two pieces of equal weight:

1. **The tool** — a multi-agent chat system that interprets MMM outputs,
   generates prioritized recommendations, and answers marketer questions. Every
   claim is grounded in the parsed model output or a cited methodology source,
   and every interpretation carries an explicit confidence level.
2. **The evaluation framework** — a benchmark suite that stress-tests the agent
   against ground-truth MMM scenarios using an LLM-as-judge, scoring accuracy,
   calibration, groundedness, actionability, failure-mode recall, and
   hallucination rate — and then *validates the judge itself* for reliability.

See [`mmm-copilot-design-doc.md`](./mmm-copilot-design-doc.md) for the full design.

---

## Highlights

- **Grounded, streamed analysis** — MMM output is parsed deterministically, then
  the agent streams a structured report (overview → per-channel reads → risks →
  ranked recommendations) over Server-Sent Events, with a live progress view.
- **Retrieval-augmented reasoning** — hybrid retrieval over a curated 14-document
  corpus of MMM methodology grounds both the initial analysis and chat answers;
  the exact chunks consulted are surfaced in the UI.
- **Multi-agent router** — questions are classified and dispatched to specialized
  handlers (interpretation, recommendation, uncertainty, comparison,
  hypothetical, methodology, clarification).
- **Bring your own model** — upload or paste your own MMM output JSON; client-side
  validation and readable backend validation errors included.
- **Trust & Evaluation page** — an in-product page surfaces the latest benchmark
  metrics, per-failure-mode recall, and judge-reliability numbers, backed by a
  live API with a committed snapshot fallback.
- **LLM-as-judge + validation** — a stronger model grades the agent on six
  dimensions; judge reliability is measured via test-retest agreement (weighted
  Cohen's κ), with a harness for validity against hand-scored labels.
- **Failure-mode catalog** — low-scoring responses are logged and categorized
  into a growing taxonomy, persisted to SQLite and browsable in a Streamlit
  dashboard.
- **LLM-optional** — with no API key, analysis falls back to a deterministic
  heuristic report and chat returns a configuration notice, so the full stack is
  demoable before any keys are wired.

## Repository layout

```
juno/
├── backend/          FastAPI service (agents, RAG, parser, evaluation, session)
│   ├── app/
│   │   ├── api/          REST + SSE endpoints (analysis, chat, samples, evaluation)
│   │   ├── agents/       initial-analysis pipeline, chat router, handlers, prompts
│   │   ├── parsers/      deterministic MMM parsing
│   │   ├── rag/          Chroma retrieval + corpus indexing + embeddings
│   │   ├── evaluation/   benchmark generator, LLM-as-judge, metrics, judge
│   │   │                 validation, failure catalog, results store, snapshot
│   │   ├── models/       Pydantic schemas
│   │   ├── session/      in-memory session store (Redis-ready)
│   │   └── core/         config + LLM client
│   ├── data/samples/     bundled sample MMM outputs
│   └── tests/
├── frontend/         Next.js 14 (App Router) + TypeScript + Tailwind
│   └── src/app/         landing (/), tool (/analyze), trust (/evaluation)
├── dashboard/        Streamlit eval-metrics dashboard
├── evaluation/       benchmark sets + eval docs
└── docs/             architecture + deployment notes
```

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind |
| Backend | FastAPI, Python 3.11+ |
| LLM (agent) | Claude Sonnet 4.5 |
| LLM (judge) | Claude Opus 4.5 |
| Embeddings | Local MiniLM by default (Chroma), optional OpenAI `text-embedding-3-small` |
| Vector DB | Chroma |
| Eval DB | SQLite |
| Eval dashboard | Streamlit |
| CI | GitHub Actions (ruff + pytest, npm lint + build) |

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
and chat returns a configuration notice — so the end-to-end app is demoable
before any keys are wired.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # BACKEND_URL defaults to http://localhost:8000
npm run dev                   # http://localhost:3000
```

Open `/` for the landing page, `/analyze` for the interactive tool, and
`/evaluation` for the Trust & Evaluation page.

### Knowledge base (RAG)

Methodology documents live in `backend/app/rag/corpus/`. To (re)build the index:

```bash
cd backend && source .venv/bin/activate
python -m app.rag.indexer --reset
```

## Evaluation

Generate benchmark cases from a synthetic MMM simulator and score the agent:

```bash
cd backend && source .venv/bin/activate
python -m app.evaluation.run_eval --n 5            # full run (agent + judge)
python -m app.evaluation.run_eval --n 5 --no-llm   # deterministic metrics only
```

Validate the judge's reliability (test-retest agreement):

```bash
python -m app.evaluation.validate_judge --reliability --n 3 --k 3
```

Runs persist to a local SQLite DB; the `/api/evaluation/summary` endpoint and the
`/evaluation` page read the latest run, falling back to a committed
`app/evaluation/snapshot.json` when no run exists (e.g. a fresh deployment).

Browse metrics and the failure catalog in the dashboard:

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

## Testing

```bash
cd backend && source .venv/bin/activate
ruff check .
pytest -q
```

CI runs the same checks plus the frontend lint + build on every push and PR
(`.github/workflows/ci.yml`).

## Deployment

Frontend deploys to **Vercel**, backend to **Render** (a `render.yaml` blueprint
and a `backend/Dockerfile` are included). See
[`docs/deployment.md`](./docs/deployment.md) for step-by-step instructions.

## Design notes

- **Parsed representation vs. interpretation** — the deterministic `MMMSummary` is
  kept separate from the natural-language `AnalysisReport` so each layer is
  independently testable. RAG grounds *methodology*, never the numeric values.
- **Explicit uncertainty** is a first-class output on every channel and
  recommendation.
- **Streaming everywhere** via SSE; session-scoped memory only (no cross-session
  state) — swap the in-memory store for Redis before scaling horizontally.

See [`docs/architecture.md`](./docs/architecture.md) for more.
