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
   The build both installs dependencies and rebuilds the RAG index:

   ```
   pip install -r requirements.txt && python -m app.rag.indexer --reset
   ```

   The index is gitignored and the free tier's disk is ephemeral, so this has to
   run on every build. Skip it and the retriever comes up empty — answers still
   generate, but with no methodology citations.

4. Set the env vars:

   | Variable | Required | Notes |
   | --- | --- | --- |
   | `ANTHROPIC_API_KEY` | yes | Live agent + judge responses. |
   | `CORS_ORIGINS` | yes | JSON array, e.g. `["https://juno.vercel.app"]`. |
   | `OPENAI_API_KEY` | no | Only if `EMBEDDING_BACKEND=openai`; the default local MiniLM needs no key. |
   | `RATE_LIMIT_PER_IP_PER_HOUR` | no | Default 20. |
   | `RATE_LIMIT_GLOBAL_PER_DAY` | no | Default 150. |

5. Health check is wired to `/health`.

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
   - `NEXT_PUBLIC_API_BASE` — the Render backend URL. **Set this before the
     first build**: `NEXT_PUBLIC_*` values are inlined at build time, so changing
     it later requires a redeploy, not just a restart.
   - `BACKEND_URL` — same URL. Only feeds the `/api` rewrite, which is now just
     a fallback for non-streaming calls if `NEXT_PUBLIC_API_BASE` is ever unset.
   - `NEXT_PUBLIC_SITE_URL` — your final public URL, so OG/Twitter cards resolve
     to absolute paths. Without it the build falls back to `VERCEL_URL`, which is
     the per-deployment hostname rather than your custom domain.
5. Deploy, then complete step 3 of the deploy order above.

## Cost control

The demo is public and every upload and chat message spends API credit.

- **Rate limits** ([`backend/app/core/rate_limit.py`](../backend/app/core/rate_limit.py))
  apply a per-IP hourly cap and a global daily ceiling. The global cap is what
  actually bounds spend — a per-IP limit alone bounds nothing, because IPs are
  trivially rotated.
- **The two bundled samples are free.** Their reports are pre-computed and
  committed under `backend/data/sample_analyses/`, replayed from disk with no LLM
  call, so the main demo path costs nothing and isn't throttled.
- **Set a hard spend cap in the Anthropic console.** It's the only limit that
  can't be defeated by a bug in this repo.

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
