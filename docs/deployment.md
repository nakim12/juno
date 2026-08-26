# Deployment

Juno deploys as two services (design doc §6):

- **Frontend** (Next.js) → **Vercel**
- **Backend** (FastAPI) → **Render** (or Railway / Fly / any Docker host)

The browser calls the backend **directly**, not through Next's `/api` rewrite.
The rewrite buffers Server-Sent Events, which collapses the streamed analysis and
chat into a single dump at the end and silently destroys the live-reasoning UX.
Talking to the backend origin means CORS has to be configured — hence the
ordering below.

## Deploy order

The two services reference each other, so deploy in this order:

1. **Backend** → gives you `https://<backend>.onrender.com`.
2. **Frontend**, with `NEXT_PUBLIC_API_BASE` set to that URL → gives you
   `https://<app>.vercel.app`.
3. **Back to the backend**: set `CORS_ORIGINS` to the Vercel URL and redeploy.

Until step 3 the browser will be blocked by CORS, which shows up as the
"can't reach the API" panel rather than an obvious CORS error.

## 1. Backend on Render

The repo includes a [`render.yaml`](../render.yaml) blueprint.

1. Push the repo to GitHub.
2. In Render: **New +** → **Blueprint** → select the `juno` repo.
3. Render reads `render.yaml` and provisions a Python web service from `backend/`.
   The build only installs dependencies:

   ```
   pip install -r requirements.txt
   ```

   It deliberately does **not** build the vector index. See
   [Retrieval on a small instance](#retrieval-on-a-small-instance).

4. Set the env vars:

   | Variable | Required | Notes |
   | --- | --- | --- |
   | `PYTHON_VERSION` | yes | Pinned to `3.13.5` in the blueprint. Render now defaults to 3.14, which has no prebuilt `pydantic-core` wheel — pip then tries to compile it from Rust and fails on the read-only cargo registry. |
   | `CORS_ORIGINS` | yes | JSON array, e.g. `["https://juno.vercel.app"]`. |
   | `DEMO_MODE` | no | Default `true`. Serves pre-computed content and refuses to spend the server's key. See [Cost control](#cost-control). |
   | `RETRIEVAL_BACKEND` | no | `lexical` in the blueprint. `auto` would pick the same thing here; see [Retrieval on a small instance](#retrieval-on-a-small-instance). |
   | `ANTHROPIC_API_KEY` | **no — leave unset** | Only needed if you turn `DEMO_MODE` off. A key that isn't deployed cannot be spent. |
   | `OPENAI_API_KEY` | no | Only if `EMBEDDING_BACKEND=openai`; the default local MiniLM needs no key. |
   | `RATE_LIMIT_PER_IP_PER_HOUR` | no | Default 20. Only applies to calls billed to the server key. |
   | `RATE_LIMIT_GLOBAL_PER_DAY` | no | Default 150. Same. |

5. Health check is wired to `/health`. Retrieval has its own:
   [`/health/rag`](#retrieval-on-a-small-instance).

### Retrieval on a small instance

The free tier gives the service 512 MB. Loading the local ONNX MiniLM embedding
model needs more than is left after the app itself, and exceeding a container's
memory limit does not raise `MemoryError` — the kernel sends `SIGKILL`. The
symptom was ugly and hard to read from the outside: the first query to touch
retrieval ran for ~45 s, the worker died, and the client got a *truncated SSE
stream with no error event*, because a closed connection is how SSE signals a
normal end. The service then restarted, so `/health` looked fine.

Nothing can be caught here, so the fix is to not load the model at all. Two
things follow from that:

- **The build doesn't index.** An index the runtime can't safely open is just
  build minutes.
- **`RETRIEVAL_BACKEND=lexical`** selects BM25 with query expansion over the same
  corpus chunks, with the same chunk ids, so a citation means the same thing
  either way ([`backend/app/rag/lexical.py`](../backend/app/rag/lexical.py)).

This costs some retrieval quality on paraphrased questions, which is where
embeddings genuinely win. Measured against the vector backend on held-out
queries, the lexical backend reproduces about 44% of its top-3 citations against
a 21% chance baseline for a corpus this size — run
`python -m scripts.compare_retrieval` to reproduce. It only affects
bring-your-own-key sessions: demo-mode answers replay citations captured when
the content was pre-computed with the vector backend.

The default, `auto`, reads the cgroup memory limit and steps down to lexical
only on a constrained container, so **on a host with ≥1.2 GB you get the vector
backend with no configuration**. To use it, restore the index build:

```
pip install -r requirements.txt && python -m app.rag.indexer --reset
```

Check which backend a deployment actually resolved:

```bash
curl -s https://<your-backend>/health/rag | jq
```

That reports the resolved backend, the memory limit that decided it, and a live
lexical query. It will not load the embedding model unless you ask for it with
`?probe=vector` — which on a small instance will kill the service, which is the
point of it being opt-in.

Prefer containers? A [`backend/Dockerfile`](../backend/Dockerfile) is included and
works on Railway / Fly / Cloud Run unchanged (they inject `$PORT`).

```bash
# Local container smoke test
cd backend && docker build -t juno-backend . && docker run -p 8000:8000 --env-file .env juno-backend
```

## 2. Frontend on Vercel

1. In Vercel: **Add New** → **Project** → import the `juno` repo.
2. Set **Root Directory** to `frontend/`.
3. Framework preset is detected as Next.js (also pinned in
   [`frontend/vercel.json`](../frontend/vercel.json)).
4. Env vars:
   - `NEXT_PUBLIC_API_BASE` — the Render backend URL. Optional: the deployed
     origin is committed as `PROD_API_BASE` in
     [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts), so the default
     already points at the right place. Set this only to override it (a fork, a
     staging backend). If you do set it, set it **before the first build** —
     `NEXT_PUBLIC_*` values are inlined at build time, so changing it later needs
     a rebuild, not a restart. On Vercel it must be a **Config** variable, not a
     secret; secrets are write-only and can't be inlined into a client bundle.
   - `BACKEND_URL` — same URL. Only feeds the `/api` rewrite, which is now just
     a fallback for non-streaming calls if `NEXT_PUBLIC_API_BASE` is ever unset.
   - `NEXT_PUBLIC_SITE_URL` — your final public URL, so OG/Twitter cards resolve
     to absolute paths. Without it the build falls back to `VERCEL_URL`, which is
     the per-deployment hostname rather than your custom domain.
5. Deploy, then complete step 3 of the deploy order above.

## Cost control

**A public deployment costs nothing to run.** With `DEMO_MODE=true` (the default)
and no `ANTHROPIC_API_KEY` on the host, there is no code path by which a visitor
can spend the owner's credit. Everything a visitor sees is either pre-computed or
deterministic:

| Surface | In demo mode | Cost |
| --- | --- | --- |
| Bundled sample analysis | Report replayed from `backend/data/sample_analyses/`, streamed so it still builds live on screen | free |
| Suggested chat questions | Answers replayed from `backend/data/sample_chats/`, with the real routed question type and citations | free |
| Any other chat message | `402` with an explanation, unless the caller supplies a key | free |
| Uploaded MMM output | Parsed, ranked, and checked for structural issues; the written interpretation is withheld | free |
| Evaluation dashboard | Committed `snapshot.json` | free |

Visitors who want live generation add their own Anthropic key in the UI. It's held
in `sessionStorage`, sent per request as `X-Anthropic-Api-Key`, and never written
to the server — see [`backend/app/core/caller_key.py`](../backend/app/core/caller_key.py).
Those requests bill the caller and skip the rate limiter.

Regenerating the pre-computed content (the only step that costs *you* money, about
$0.30, and only when prompts change):

```bash
cd backend
python -m app.agents.precompute_chat            # curated chat answers
python -m app.agents.precompute_chat --list     # see the questions first
```

Sample *reports* are cached the first time each sample is loaded with a key
present; commit the resulting JSON under `backend/data/`.

If you do turn `DEMO_MODE` off and deploy a key, two guards remain, neither of
which is a substitute for the above: the
[rate limiter](../backend/app/core/rate_limit.py) (per-IP hourly plus a global
daily ceiling, which is the part that actually bounds spend, since IPs rotate
freely) and a hard spend cap set in the Anthropic console — the only limit that
can't be defeated by a bug in this repo. Note that request-count limits bound the
*rate*, not the *total*: a determined visitor can still drain a balance over days.

## Notes

- **Cold starts.** Render's free tier sleeps after inactivity and takes ~50s to
  wake. The site pings `/health` on first load so the container is usually warm
  by the time anyone clicks through, and `/analyze` retries on a backoff for
  about a minute while showing a "starting the demo server" state instead of an
  error.
- **The site degrades gracefully without a backend.** `/evaluation` falls back to
  the committed `snapshot.json`, so the benchmark numbers render even on a cold
  or unconfigured deployment.
- Session state is in-memory (design doc §5.7), as is the rate limiter; a single
  backend instance is fine for the demo. Both need Redis before scaling out.
- The eval database lives on the backend's local disk and is also ephemeral on
  the free tier. Committed snapshot data is what the Trust page reads in
  production.
