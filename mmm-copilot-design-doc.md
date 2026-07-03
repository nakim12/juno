# MMM Copilot: Design Document

**Author:** Nathan Kim
**Status:** Draft v1
**Last updated:** June 2026

---

## 0. TL;DR

MMM Copilot is an agentic AI system that turns Marketing Mix Model outputs into actionable business decisions through a conversational interface, backed by a rigorous evaluation framework that quantifies whether the agent's advice can be trusted.

The project has two pieces of equal weight:

1. **The tool itself**: a multi-agent chat system that interprets MMM outputs, generates recommendations, and answers marketer questions with grounded reasoning
2. **The evaluation framework**: a benchmark suite that stress-tests the agent against ground-truth MMM outputs generated from your BlueAlpha simulator, using LLM-as-judge to quantify accuracy, calibration, and hallucination rate

Building both pieces is what makes the project rare. Most portfolio projects are "cool demos." This one demonstrates production AI thinking: you built a system, and you also built the harness to prove it works.

---

## 1. Problem Statement

Marketing Mix Models produce technically rich outputs (coefficients, uncertainty intervals, saturation curves, adstock parameters, diagnostic plots) that are largely opaque to the people who need to act on them. Marketers and business leaders want three things:

1. **Interpretation**: what is this model actually saying?
2. **Recommendation**: what should we do differently?
3. **Trust**: how confident should we be in the answer?

Today, this gap is filled through one of three inadequate paths:

- **Consultants**: expensive, slow, and inconsistent
- **In-house DS**: bandwidth-constrained, often bottlenecked
- **Vendor dashboards**: static, no reasoning layer, no follow-up questions

An LLM-based copilot can bridge this gap, but only if the advice is actually trustworthy. Most AI copilots today are impressive-looking demos with no rigorous evaluation of whether the advice is good. That's the gap this project fills.

---

## 2. Goals and Non-Goals

### Goals

1. Build a conversational agent that produces useful, well-grounded interpretations of MMM outputs
2. Build an evaluation framework that quantifies agent quality on defensible metrics
3. Demonstrate structured thinking about production LLM systems (agent design, RAG, evaluation, uncertainty)
4. Ship a live, publicly demoable version deployed on infrastructure that mirrors production stacks
5. Produce a technical writeup that documents architecture and evaluation results

### Non-Goals

1. Solving the real business problem for actual companies (no marketing effort, no onboarding, no support)
2. Handling arbitrary user data with production security guarantees (synthetic data only for demo purposes)
3. Multi-user support, accounts, or persistence beyond session state
4. Being a full MMM training or building system (we consume MMM outputs, we do not fit models)
5. Multi-provider LLM support (Claude only for MVP; noted as post-MVP extension)

Explicit non-goals matter because they define what "done" means. Every hour spent on a non-goal is an hour not spent on the differentiators.

---

## 3. Target User and Success Criteria

### Primary User: Interview Demonstration

The user of this system is a Nathan-in-an-interview scenario. Success is defined by whether an interviewer at Sierra, Recast, Trade Desk, or a comparable company:

1. Understands what was built within 60 seconds of the demo starting
2. Recognizes the architectural sophistication (multi-agent, RAG, eval framework) as beyond typical portfolio work
3. Has substantive follow-up questions about design decisions, tradeoffs, and next steps
4. Considers the project as evidence of production AI thinking, not just tinkering

### Secondary User: Someone Who Actually Uses It

While the primary user is an interviewer, the tool should be usable by a curious marketer or data scientist who lands on the demo. That means:

1. Pre-loaded sample MMM outputs so the user can start experiencing the tool in under 30 seconds
2. Clear onboarding text that explains what the tool does
3. Responsive UI (streaming chat, no unexplained loading states)
4. JSON upload path for anyone who wants to bring their own MMM output

### Success Criteria

The project is a success when:

1. A working deployment is publicly accessible and stable
2. The evaluation framework produces reproducible metrics that Nathan can defend in an interview
3. The technical writeup exists and is linkable from the portfolio site
4. At least one interview conversation references the project unprompted
5. The failure mode catalog documents at least 10 categorized agent failure patterns

---

## 4. System Architecture

### 4.1 High-Level Component Diagram

```
+-----------------------------------------------------------+
|                       Frontend (Next.js)                  |
|   +---------------------+    +-----------------------+    |
|   |   MMM Input Panel   |    |   Chat Interface      |    |
|   |   (upload or        |    |   (streaming          |    |
|   |    sample loader)   |    |    responses)         |    |
|   +---------------------+    +-----------------------+    |
+-----------------------------|-----------------------------+
                              |
                              | HTTP + SSE
                              |
+-----------------------------|-----------------------------+
|                    Backend (FastAPI)                      |
|                                                           |
|   +----------------+   +-------------------------------+  |
|   |   Session      |   |   Agent Orchestration Layer   |  |
|   |   Manager      |<->|                               |  |
|   +----------------+   |   +------------------------+  |  |
|                        |   |   Initial Analysis     |  |  |
|                        |   |   Pipeline             |  |  |
|                        |   +------------------------+  |  |
|                        |                               |  |
|                        |   +------------------------+  |  |
|                        |   |   Chat Agent           |  |  |
|                        |   |   (Router + Handlers)  |  |  |
|                        |   +------------------------+  |  |
|                        +-------------------------------+  |
|                              |                            |
|                              v                            |
|   +----------------+   +----------------+                 |
|   |   Claude API   |   |   RAG Layer    |                 |
|   |   (Sonnet 4)   |   |   (Chroma)     |                 |
|   +----------------+   +----------------+                 |
|                              |                            |
+-----------------------------|-----------------------------+
                              |
                              v
                    +---------------------+
                    |   Knowledge Base    |
                    |   (curated MMM      |
                    |    methodology)     |
                    +---------------------+

+-----------------------------------------------------------+
|                Evaluation Framework (separate)            |
|                                                           |
|   +--------------------+   +-------------------------+    |
|   |   BlueAlpha        |   |   Benchmark Runner      |    |
|   |   Simulator        |-->|   (calls agent API      |    |
|   |   (ground truth)   |   |    on N test cases)     |    |
|   +--------------------+   +-------------------------+    |
|                                        |                  |
|                                        v                  |
|                            +-------------------------+    |
|                            |   LLM-as-Judge          |    |
|                            |   (Opus grades Sonnet)  |    |
|                            +-------------------------+    |
|                                        |                  |
|                                        v                  |
|                            +-------------------------+    |
|                            |   Metrics Dashboard     |    |
|                            |   (Streamlit)           |    |
|                            +-------------------------+    |
+-----------------------------------------------------------+
```

### 4.2 Core Design Principles

1. **Separation of "reason" and "answer"**: The initial analysis pipeline produces a structured internal representation of what the model says. The chat agent then answers questions grounded in that representation. This separation lets the eval framework test each layer independently.

2. **Explicit uncertainty is a first-class output**: Every recommendation carries a confidence score. Every response cites which parts come from the MMM output vs. from methodology context vs. from LLM inference.

3. **RAG grounds methodology, not values**: The MMM output values (ROI, adstock, saturation) are always sourced from the parsed input. RAG retrieves methodology context (how to interpret adstock decay, what saturation means, common failure modes) to structure the reasoning.

4. **Session-scoped memory only**: No cross-session state. Each demo starts fresh. This simplifies the system and makes evaluation runs reproducible.

5. **Streaming everywhere**: Chat responses stream token-by-token. Initial analysis reports also stream section-by-section. Perceived latency matters for the demo feel.

---

## 5. Component Design

### 5.1 Initial Analysis Pipeline

Triggered once when the user loads an MMM output. Produces a structured report cached in session state.

**Stages:**

**Stage 1: Parser**

- Input: raw MMM output (JSON schema documented below)
- Output: structured `MMMSummary` object with:
  - Per-channel: spend, ROI point estimate, ROI CI, saturation params, adstock params
  - Model-level: R-squared or equivalent, MAPE, holdout metrics, data span
  - Detected issues (missing intervals, extreme saturation values, etc.)
- Deterministic. Not an LLM call. Fast.

**Stage 2: Context Retrieval**

- Input: `MMMSummary`
- Output: list of relevant knowledge base chunks
- Uses hybrid retrieval: keyword match on channel names and structural features, plus semantic search on the summary
- Retrieves ~8-12 chunks that are relevant to the specific model characteristics detected

**Stage 3: Analysis Agent (LLM call)**

- Model: Claude Sonnet 4.5 (or the current strongest reasoning model at build time)
- Input: `MMMSummary` + retrieved context
- Output: structured JSON report with:
  - Per-channel interpretation
  - Confidence assessment (high / medium / low + reasoning)
  - Structural risks flagged
  - Suggested actions with priority ranking
  - Suggested validation steps (lift tests, holdout, etc.)
- Uses Claude's structured output feature (JSON schema enforcement)
- Prompt is versioned and stored in the repo

**Stage 4: Cache in session state**

The report is cached because the chat agent needs it. Regenerating the report on every chat turn would be expensive and unnecessary.

### 5.2 Interactive Chat Agent

Turn-by-turn conversation about the loaded MMM output.

**Architecture: Router + Specialized Handlers**

```
User question
    ↓
[Router] classifies into one of:
    - INTERPRETATION: what does X mean in this model?
    - RECOMMENDATION: what should I do about Y?
    - METHODOLOGY: how does MMM handle Z?
    - HYPOTHETICAL: what if I did A?
    - COMPARISON: is B better than C?
    - UNCERTAINTY: how confident should I be about D?
    - CLARIFICATION: I don't understand E from your previous response
    ↓
[Handler for that category] does:
    - Retrieves relevant sections of the cached report
    - Retrieves additional methodology context if needed
    - Constructs prompt with grounding materials
    - Calls LLM with structured output
    - Streams response back
    ↓
[State updater] records the exchange in session state
```

**Why this pattern:**

- Routing lets us tune prompts and retrieval strategies per question type
- Different handlers can use different tools (e.g., HYPOTHETICAL might use a calculation tool)
- Consistent structure makes evaluation easier
- Similar architectural pattern to Romus 4-loop system, so Nathan can defend it from experience

**Handler details:**

Each handler follows a template:

1. Load relevant portions of the cached report
2. Load prior conversation context (last 3 turns typically)
3. Retrieve additional knowledge base chunks if question is methodology-flavored
4. Construct prompt with explicit grounding sections
5. Call LLM with system prompt tuned for that question type
6. Post-process response to extract citations
7. Stream response with citations to frontend

**Response format:**

Every chat response has three parts:

- **Answer** (natural language, streamed)
- **Grounding** (which parts of the MMM output and knowledge base were used)
- **Confidence** (high / medium / low, with a one-sentence explanation)

This tripartite structure enforces transparency and enables the evaluation harness to score groundedness.

### 5.3 Knowledge Base and RAG

**Corpus contents:**

The knowledge base is a curated set of documents on MMM methodology. Target 30-50 high-quality documents. Sources:

- Academic papers on MMM, causal inference, and Bayesian attribution (5-10 papers)
- Recast's public blog (Tom Vladeck and Michael Kaminsky's posts)
- Google's Meridian documentation and papers
- Meta's Robyn documentation
- Blog posts from other credible practitioners (Northbeam, Tinuiti, etc.)
- Foundational textbook excerpts (with rights consideration)

Each document is chunked into ~500-token segments with metadata tags:

- `topic`: adstock, saturation, causal_inference, calibration, etc.
- `source`: paper, blog, docs
- `credibility_tier`: academic, industry_practitioner, vendor_docs

**Embedding and storage:**

- Embeddings: OpenAI text-embedding-3-small (cost-efficient, sufficient for this corpus size)
- Vector store: Chroma DB (self-hosted, no ongoing costs, easy local dev)
- Metadata filters allow retrieval by topic, source, tier

**Retrieval strategy:**

Hybrid retrieval:

1. Structural keyword match on the MMM summary (channels mentioned, features detected)
2. Semantic search on the user's question or the summary
3. Rerank top-20 results using a lightweight rerank model (or cross-encoder)
4. Return top-8 to the LLM

The reranking step is important because pure semantic search over a small corpus produces noisy results. A cross-encoder rerank meaningfully improves relevance.

### 5.4 Evaluation Framework

The centerpiece of the project's differentiation. This is what elevates the project from "cool demo" to "someone who thinks about production AI."

**Ground truth generation:**

Uses Nathan's existing BlueAlpha simulator with a controlled sweep:

- 100 diverse MMM output scenarios
- Sweep across: channel count (3-10), spend range, seasonality strength, adstock decay range, saturation curve shapes, noise level, data span (26-104 weeks)
- For each scenario, ground truth includes:
  - True per-channel ROI
  - True saturation and adstock parameters
  - True optimal budget allocation
  - Known model failure modes (e.g., "this scenario has multicollinearity between Meta and Instagram")
- Store as a versioned benchmark set

**Reference interpretations:**

For each benchmark case, we generate an ideal interpretation as a reference. Two approaches:

- Semi-manual: Nathan writes reference interpretations for 20 cases; a stronger model (Claude Opus 4.5) writes the rest based on ground truth
- Fully automated: Claude Opus 4.5 with access to ground truth generates all reference interpretations

Start with fully automated for scale; hand-audit 20 to check that references are actually good. Update reference generation prompt as needed.

**LLM-as-Judge harness:**

- Judge model: Claude Opus 4.5 (different from agent's Sonnet to reduce same-model bias)
- Structured rubric with dimensions:
  - **Accuracy**: does the agent's channel ranking match ground truth?
  - **Calibration**: when the agent expressed low confidence, was it right to?
  - **Groundedness**: does every claim tie back to the MMM output or a cited source?
  - **Actionability**: is the recommendation specific enough to execute?
  - **Failure mode detection**: did the agent flag known model risks?
  - **Hallucination rate**: did the agent make claims not supported by the MMM output?
- Judge outputs a score (0-5) per dimension with reasoning
- Deterministic scoring for accuracy (compare channel ranking programmatically); LLM scoring for the rest

**Metrics:**

Aggregate across the benchmark set:

- **Accuracy**: Spearman rank correlation between agent's channel ranking and ground truth ranking
- **Calibration**: expected calibration error (ECE) between agent's confidence and ground truth correctness
- **Groundedness**: fraction of claims with valid citations
- **Actionability**: mean judge score
- **Hallucination**: fraction of claims that don't match ground truth or cited sources
- **Failure mode detection**: recall on known failure modes

**Failure mode catalog:**

For each benchmark case where the agent scores below a threshold, log:

- Input scenario
- Agent's response
- Judge's reasoning for the low score
- Categorization of failure type

Over time, build a taxonomy of failure modes. Publish this. Failure mode catalogs are exactly what LLM Evals teams at real AI companies build.

**Metrics dashboard:**

A separate Streamlit app that displays evaluation results:

- Per-dimension scores over time (as the agent prompts evolve)
- Per-scenario-type breakdown (which failure modes are most common?)
- Failure mode catalog browser
- Comparison mode (compare agent v1.0 vs. v1.1)

This dashboard is a portfolio piece in itself. Interviewers will find it.

### 5.5 Frontend

**Framework:** Next.js 14 (App Router) with TypeScript.

**Why Next.js over pure React:**

- Server components for cleaner architecture
- Built-in API routes for BFF (backend-for-frontend) pattern
- One-click Vercel deployment
- Streaming support via React Server Components and Suspense

**UI library:** shadcn/ui + Tailwind.

**Why shadcn/ui:**

- Not a heavy component library; it's copy-paste components
- Excellent visual quality out of the box
- Full control over customization
- Matches modern AI product design language (see Perplexity, Vercel v0)

**Main views:**

1. **Landing / Input Panel**
   - Sample MMM selector (5-10 pre-loaded scenarios with descriptive names like "3-channel small budget", "8-channel multi-market", "with obvious saturation")
   - JSON upload button
   - "Generate your own with BlueAlpha Simulator" link
   - Brief onboarding copy

2. **Analysis Report View**
   - Streamed generation of the initial report
   - Sections: Overview, Per-Channel Analysis, Risks, Recommendations
   - Confidence badges throughout
   - Citations expandable inline
   - "Chat about this" button transitions to chat view

3. **Chat View**
   - Standard chat UI with streaming responses
   - Every response shows:
     - Answer body
     - Confidence badge
     - Expandable grounding section (shows which parts of MMM output and knowledge base were used)
   - Session state persists during the browser session
   - Sidebar shows a summary of the loaded MMM output for quick reference

4. **Eval Dashboard (separate URL)**
   - Streamlit app embedded via iframe or linked externally
   - Metrics overview
   - Failure mode browser
   - Live benchmark runner (kick off a fresh eval run)

### 5.6 Backend

**Framework:** FastAPI with Python 3.11+.

**Architecture:** Modular, testable, roughly follows clean architecture principles.

**Directory structure:**

```
backend/
├── api/                    # FastAPI routes
│   ├── analysis.py         # POST /analyze
│   ├── chat.py             # POST /chat (streaming)
│   └── session.py          # Session management
├── agents/
│   ├── initial_analysis.py # Multi-stage analysis pipeline
│   ├── chat_router.py      # Routes questions to handlers
│   ├── handlers/           # One handler per question type
│   │   ├── interpretation.py
│   │   ├── recommendation.py
│   │   ├── methodology.py
│   │   ├── hypothetical.py
│   │   ├── comparison.py
│   │   ├── uncertainty.py
│   │   └── clarification.py
│   └── prompts/            # Versioned prompt templates
├── parsers/
│   └── mmm_parser.py       # Deterministic MMM structure extraction
├── rag/
│   ├── retriever.py        # Chroma retrieval + rerank
│   ├── indexer.py          # Corpus indexing (batch job)
│   └── corpus/             # Source documents (chunks stored elsewhere)
├── evaluation/
│   ├── benchmark_generator.py  # Generates benchmark set
│   ├── judge.py                # LLM-as-judge harness
│   ├── metrics.py              # Aggregate metrics
│   └── failure_catalog.py      # Failure mode logging
├── models/
│   ├── mmm_summary.py     # Pydantic schemas
│   ├── analysis_report.py
│   └── chat_message.py
├── session/
│   └── store.py           # In-memory session store (Redis in prod)
└── main.py
```

**Key API endpoints:**

- `POST /api/analyze`: takes an MMM output JSON, returns a streaming initial report and a session ID
- `POST /api/chat`: takes a message + session ID, streams a response
- `GET /api/session/{id}`: returns cached report for a session (for re-hydration)
- `GET /api/samples`: returns list of pre-loaded sample MMM outputs
- `POST /api/samples/{id}/load`: loads a sample into a new session

**Streaming:** Server-Sent Events (SSE) for both analysis and chat endpoints. Simpler than WebSockets, well-supported by browsers, works cleanly with FastAPI's `StreamingResponse`.

**LLM calls:** All Claude API calls use structured output where possible. All calls are logged for later evaluation. Prompts are versioned in a `prompts/` directory and loaded at request time so evolution can be tracked.

### 5.7 Data Model

**MMM Output Schema (input):**

```python
class MMMOutput(BaseModel):
    metadata: MMMMetadata           # data span, model type, timestamp
    channels: list[ChannelOutput]   # per-channel results
    model_diagnostics: Diagnostics  # R^2, MAPE, holdout metrics
    optional: Optional[ExtendedData]  # priors, MCMC diagnostics, etc.

class ChannelOutput(BaseModel):
    name: str
    spend_weekly: list[float]        # weekly spend series
    roi_point: float
    roi_ci: tuple[float, float]      # (lower, upper) 95% CI
    adstock_decay: float
    saturation_params: SaturationParams
    contribution_pct: float          # % of total attribution
```

**Analysis Report Schema (output of initial analysis):**

```python
class AnalysisReport(BaseModel):
    session_id: str
    overview: str                    # Natural language summary
    per_channel: list[ChannelAnalysis]
    structural_risks: list[Risk]
    recommendations: list[Recommendation]
    validation_suggestions: list[ValidationStep]
    metadata: ReportMetadata

class ChannelAnalysis(BaseModel):
    channel_name: str
    interpretation: str
    confidence: Literal["high", "medium", "low"]
    confidence_reasoning: str
    citations: list[Citation]        # From MMM output or knowledge base

class Recommendation(BaseModel):
    action: str
    priority: Literal["high", "medium", "low"]
    rationale: str
    confidence: Literal["high", "medium", "low"]
    dependencies: list[str]          # e.g., "requires lift test validation"
    citations: list[Citation]
```

**Session state:**

- In-memory dict keyed by session ID (Redis in prod, dict in dev)
- Contains: original MMM output, analysis report, conversation history, retrieval logs
- TTL: 2 hours (long enough for a demo session, short enough to keep memory small)

**Evaluation storage:**

- SQLite for MVP (portable, no infra)
- Tables: `benchmark_cases`, `agent_runs`, `judge_scores`, `failure_modes`
- Can migrate to Postgres if it grows

---

## 6. Tech Stack Summary

| Layer | Choice | Rationale |
|---|---|---|
| Frontend framework | Next.js 14 App Router | Streaming, server components, Vercel one-click deploy |
| UI components | shadcn/ui + Tailwind | Modern design, full control, no bloat |
| Backend framework | FastAPI (Python 3.11+) | Nathan knows it from Romus/Dialed, async streaming |
| LLM (agent) | Claude Sonnet 4.5 | Strong reasoning, familiar API, cost-efficient |
| LLM (judge) | Claude Opus 4.5 | Different model reduces same-model bias in eval |
| Embeddings | OpenAI text-embedding-3-small | Cost-efficient, sufficient for small corpus |
| Vector DB | Chroma | Self-hosted, free, easy dev |
| Session store | In-memory dict (dev), Redis (prod-ready) | Simple, TTL-friendly |
| Eval database | SQLite (MVP), Postgres (extension) | Portable, no infra to start |
| Frontend deploy | Vercel | Free tier, one-click, matches Romus stack |
| Backend deploy | Railway or Render | Free tier, easy FastAPI deploy |
| Eval dashboard | Streamlit | Fast to build, matches "data tool" aesthetic |

---

## 7. Data Flow

### 7.1 Initial Analysis Flow

```
1. User selects sample OR uploads JSON
2. Frontend POSTs to /api/analyze with MMM output
3. Backend creates session, returns session_id
4. Frontend opens SSE stream to /api/analyze/{session_id}/stream
5. Backend runs:
   a. Parser produces MMMSummary
   b. Retriever fetches relevant knowledge chunks
   c. Analysis Agent generates structured report
   d. Streaming response emitted section-by-section
6. Frontend renders report progressively
7. Session state cached in backend for chat
```

### 7.2 Chat Flow

```
1. User types question, presses send
2. Frontend POSTs to /api/chat with session_id + message
3. Backend runs:
   a. Router classifies question type
   b. Handler for that type loads relevant report sections
   c. Additional knowledge retrieval if methodology question
   d. Handler constructs prompt
   e. Claude API called with streaming
   f. Response streamed back with structured metadata (grounding, confidence)
4. Frontend renders response with expandable grounding
5. Session state updated with new turn
```

### 7.3 Evaluation Flow (offline, batch)

```
1. Benchmark generator produces N=100 MMM outputs via BlueAlpha simulator
2. Reference interpretations generated by Claude Opus with ground truth access
3. Benchmark runner iterates through cases:
   a. Loads case into fresh session
   b. Triggers initial analysis (captures report)
   c. Runs scripted chat questions (captures responses)
4. LLM-as-judge scores each output against reference
5. Metrics aggregated and stored
6. Failure modes categorized and logged
7. Dashboard updated
```

---

## 8. Build Phases

Phase-by-phase build plan. Each phase produces a shippable increment.

### Phase 1: Foundation (Weeks 1-2)

**Goal:** end-to-end skeleton that works with a hardcoded sample and a single agent.

- FastAPI backend with basic endpoints
- Next.js frontend with basic UI
- Claude API integration
- Hardcoded MMM output sample
- Single-pass analysis (no multi-agent yet, no RAG yet)
- Basic chat with no routing (all questions go to one prompt)
- Vercel + Railway deployment working end-to-end

**Deliverable:** Public URL where someone can see the loaded sample MMM output and ask a question about it.

### Phase 2: RAG and Knowledge Base (Weeks 3-4)

**Goal:** Retrieval-grounded responses.

- Curate initial corpus (30-50 documents)
- Chroma setup and indexing pipeline
- Retrieval integration into analysis pipeline
- Retrieval integration into chat responses
- Citation tracking end-to-end
- Frontend expandable citation UI

**Deliverable:** All responses cite either MMM output or knowledge base chunks.

### Phase 3: Multi-Agent Architecture (Weeks 5-6)

**Goal:** Sophisticated agent architecture worth showing off.

- Refactor initial analysis into multi-stage pipeline (Parser -> Context -> Analysis -> Recommendation)
- Router-based chat with specialized handlers
- Structured output enforcement everywhere
- Confidence scoring on every output
- Prompt versioning system

**Deliverable:** Chat responses are noticeably better-grounded and more useful than Phase 1.

### Phase 4: Evaluation Framework (Weeks 7-9)

**Goal:** The differentiating component.

- Benchmark generator using BlueAlpha simulator (100 cases)
- Reference interpretation generation with Opus
- LLM-as-judge harness
- Metrics pipeline
- Failure mode logging
- Streamlit dashboard for eval results

**Deliverable:** Metrics dashboard with real numbers. First failure mode catalog entries.

### Phase 5: Polish and Writeup (Weeks 10-12)

**Goal:** Portfolio-ready.

- UI polish (loading states, error handling, mobile responsiveness)
- Sample MMM outputs curated and named
- BlueAlpha simulator link integration
- Technical writeup published (2000-3000 words)
- Portfolio site updated
- LinkedIn post drafted

**Deliverable:** Project is stable, demoable, and documented.

### Phase 6: Iteration (ongoing)

**Goal:** Continuous improvement based on eval results.

- Address top failure modes
- Improve prompts based on metrics
- Add new benchmark cases as edge cases emerge
- Track metrics over time to demonstrate improvement

**Deliverable:** Metrics dashboard shows quality trending upward. Interviewers can see the iteration story.

---

## 9. Evaluation Strategy

### 9.1 What we measure

Six dimensions, weighted by interview relevance:

| Dimension | Weight | Method | Target |
|---|---|---|---|
| Accuracy (channel ranking) | 25% | Spearman correlation with ground truth | > 0.85 |
| Calibration (confidence-correctness match) | 20% | Expected Calibration Error (ECE) | < 0.10 |
| Groundedness (claims trace to sources) | 20% | LLM judge fraction | > 0.90 |
| Actionability (specific, executable advice) | 15% | LLM judge score | > 4.0/5 |
| Failure mode detection (flagging known risks) | 10% | Recall on tagged risks | > 0.75 |
| Hallucination rate | 10% | LLM judge fraction | < 0.05 |

Weights are approximate; the point is that these are the dimensions we care about and can defend.

### 9.2 Judge validation

Before trusting the judge, validate it:

- Hand-score 20 outputs across dimensions
- Compare with judge scores
- Compute inter-rater agreement (Cohen's kappa or similar)
- If agreement is low, refine the judge rubric

Judge validation is important because "LLM-as-judge" can look rigorous while being noise. Nathan should be able to say "here's how I validated my judge" in interviews.

### 9.3 Regression testing

Every time the agent prompts change:

- Run full benchmark suite
- Compare metrics against previous version
- Flag regressions on any dimension
- Log to metrics dashboard for trending

### 9.4 Failure mode taxonomy

As failures accumulate, categorize them. Expected categories:

- **Overconfidence on sparse data**: Agent expresses high confidence when the MMM output has wide CIs
- **Missing structural risks**: Agent doesn't flag multicollinearity or extrapolation
- **Weak recommendations**: "Consider testing" instead of specific actions
- **Methodology confusion**: Agent misapplies causal inference concepts
- **Hallucination on channel names**: Agent invents channels not in the output
- **Over-hedging**: Agent refuses to give a recommendation when the data supports one
- **Under-hedging**: Agent gives a recommendation without noting uncertainty

Aim for at least 10 documented failure modes in the catalog. This is the artifact that most differentiates the project.

---

## 10. Risks and Mitigations

### R1: LLM API costs

**Risk:** Running 100-case benchmark with judge = ~200 Claude calls per eval run. At even $0.05/call, that's $10/run. Multiple runs = real money.

**Mitigation:**
- Cache aggressively during dev
- Use Haiku for iteration, promote to Sonnet for final benchmarks
- Anthropic sometimes offers credits for portfolio projects; worth asking
- Budget: $200 total for the project is a reasonable cap

### R2: The evaluation framework is the hardest part

**Risk:** Building an eval framework is significantly harder than building a chat interface. Easy to skimp on this and end up with just another LLM demo.

**Mitigation:**
- Force yourself to build eval before polishing UI
- Phase 4 comes before Phase 5 in the build plan for this reason
- Even a small eval framework (20 cases, 3 dimensions) is more differentiating than none

### R3: Corpus quality determines RAG quality

**Risk:** Poorly-curated knowledge base = irrelevant retrievals = weak agent responses.

**Mitigation:**
- Spend real time on corpus curation
- Chunk with careful metadata tagging
- Test retrieval quality manually before building the full agent
- Reserve time for corpus expansion after Phase 3 (once you know what's missing)

### R4: Prompt engineering churn

**Risk:** LLM output quality varies wildly with prompt phrasing. Easy to spend infinite time here.

**Mitigation:**
- Version prompts in the repo from day one
- Only change prompts when eval metrics move in the right direction
- Time-box prompt engineering per phase

### R5: Ambitious scope

**Risk:** The full plan is 100-150 hours of work. Real risk of never shipping.

**Mitigation:**
- Ship end of Phase 1 as MVP even if it's rough
- Public deployment forces continued iteration
- Weekly check-ins with yourself: "what did I actually ship this week?"

### R6: BlueAlpha simulator drift

**Risk:** Your BlueAlpha simulator was built for BlueAlpha's specific MMM setup. It might not generate MMM outputs that match the schema your Copilot expects.

**Mitigation:**
- Explicit schema mapping layer between simulator output and Copilot input
- Document the schema clearly
- Include synthetic examples that don't come from the simulator to cover edge cases

---

## 11. Post-MVP Extensions

Ideas for after the core project ships. Documented here to defend "what's next" in interviews.

1. **Multi-provider LLM support**: benchmark GPT-4, Gemini, Llama against Claude on the same eval suite. Compare quality and cost.

2. **Fine-tuned interpretation model**: use the benchmark cases + reference interpretations to fine-tune a small open-source model. Compare against Claude.

3. **Real MMM tool integrations**: build parsers for actual outputs from Meridian, Robyn, Recast (with permission).

4. **Uncertainty calibration**: use conformal prediction on the confidence scores.

5. **User feedback loop**: thumbs up/down on responses, use signal to improve prompts or retrain rerank model.

6. **Comparison mode**: load two MMM outputs (before/after a lift test, or two vendors) and compare.

7. **Report export**: generate a PDF report from the analysis for offline sharing.

8. **API version**: expose the agent as an API for programmatic access.

---

## 12. Interview Narrative

The narrative structure to have ready when this comes up in interviews.

**One-sentence pitch:**
"MMM Copilot is an agentic AI system that interprets Marketing Mix Model outputs for marketers, plus a rigorous evaluation framework that quantifies whether the agent's advice can be trusted."

**Why you built it:**
"At BlueAlpha I built infrastructure to test whether MMMs are trustworthy. My hackathon work on Romus and Dialed showed me agentic AI could bridge the gap between model outputs and business action. But I noticed most AI copilots don't have rigorous evaluation of whether their advice is actually good. I wanted to build both the tool and the harness to prove it works."

**Architecture depth:**

Have ready:
- Multi-agent architecture with router pattern
- Separation of parsed representation from natural language interpretation
- Grounded citations with explicit uncertainty
- LLM-as-judge harness with judge validation
- Failure mode catalog

**What was hard:**

- Judge validation: making sure the eval isn't rubber-stamping the agent
- Calibration: getting confidence scores that actually correlate with correctness
- Groundedness: enforcing citations without making responses feel robotic
- Corpus curation: balancing academic rigor and practical usefulness

**What you'd do next:**

Any of the post-MVP extensions, framed as "if I had unlimited time" or "if this became a real product."

---

## 13. Open Questions

Things that need decisions made during build, but that we've deferred here:

1. **Exact prompt structure**: iterate during build; version in repo
2. **Corpus specific document selection**: start with 15 documents, expand to 40 by Phase 3
3. **BlueAlpha simulator interface**: whether to call it as an API, run it as a subprocess, or copy over just the data generation logic
4. **Sample MMM output specifics**: what scenarios to feature (3-channel simple, 8-channel complex, obviously saturated, obviously undersized, etc.)
5. **Judge validation sample size**: 20 is a first target; may need to grow if agreement is low
6. **Failure mode taxonomy**: emerges from data during Phase 4; don't preemptively categorize

These questions get answered as the project develops. Do not try to resolve them upfront.

---

## 14. Success Definition Recap

The project succeeds when:

1. A live public deployment is stable and demonstrable
2. Metrics dashboard shows meaningful, defensible numbers on 6 evaluation dimensions
3. Failure mode catalog contains at least 10 categorized entries
4. Technical writeup is published and linkable
5. At least one interview conversation surfaces the project unprompted
6. Nathan can defend every architectural decision in a technical interview without hedging

That last one is the truest measure. If you can talk about this project fluently for an hour in a technical interview, without notes, the project succeeded regardless of stars, forks, or users.

---

## Appendix A: Suggested Starting Corpus

Documents to prioritize for the initial knowledge base build. Not exhaustive; expand as gaps emerge.

**Academic / foundational:**

- Chan and Perry, "Challenges and Opportunities in Media Mix Modeling" (Google)
- Bayesian methods for Marketing Mix Modeling (various authors)
- Recent papers on causal inference for advertising (search Semantic Scholar for latest)

**Industry practitioner:**

- Tom Vladeck's Recast blog (posts on judging MMM performance, model evaluation)
- Michael Kaminsky's writing on MMM mistakes
- Robyn documentation (Meta's open source MMM)
- Meridian documentation (Google's open source MMM)
- Northbeam blog on attribution
- Analytic Edge, Tinuiti, and similar practitioner blogs

**Textbook excerpts:**

- Bayesian Data Analysis (Gelman et al.), sections on hierarchical models
- Causal Inference: The Mixtape (Cunningham), sections on synthetic controls (relevant for lift testing context)

Aim for 30-50 documents total. Better to have fewer high-quality documents than many mediocre ones.

---

## Appendix B: Prompt Engineering Principles

Design principles for the prompts (not the actual prompts, which are iterated in the repo):

1. **Grounding first**: every prompt includes explicit sections labeling MMM output values vs. methodology context vs. inference
2. **Confidence is required**: no response is allowed without an explicit confidence assessment
3. **Structured output where possible**: JSON schema enforcement for classification, structured output for analysis reports
4. **Chain-of-thought behind the scenes**: reasoning happens in a hidden field, cleaned response goes to user
5. **Refusal patterns**: agent refuses to answer when insufficient grounding exists ("I don't have enough information to say X")
6. **Explicit uncertainty language**: agent uses "the model suggests X, but the confidence interval is wide" rather than "X is true"

These are the guardrails that separate a copilot from a bullshit generator.

---

*End of document.*
