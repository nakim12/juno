# Deployment

Juno deploys as two services (design doc §6):

- **Frontend** (Next.js) → **Vercel**
- **Backend** (FastAPI) → **Render** (or Railway / Fly / any Docker host)

The frontend proxies `/api/*` to the backend via `next.config.mjs`, so the
browser only ever talks to the Vercel origin.

## 1. Backend on Render

The repo includes a [`render.yaml`](../render.yaml) blueprint.

1. Push the repo to GitHub.
2. In Render: **New +** → **Blueprint** → select the `juno` repo.
3. Render reads `render.yaml` and provisions a Python web service from
   `backend/` with `startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Set the secret env vars in the dashboard:
   - `ANTHROPIC_API_KEY` — required for live LLM responses.
   - `OPENAI_API_KEY` — embeddings (Phase 2 RAG).
   - `CORS_ORIGINS` — JSON array of allowed origins, e.g. `["https://juno.vercel.app"]`.
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
4. Add env var `BACKEND_URL` = your Render backend URL
   (e.g. `https://juno-backend.onrender.com`).
5. Deploy. Update the backend's `CORS_ORIGINS` with the resulting Vercel URL.

## Notes

- SSE streaming (`/api/analyze/.../stream`, `/api/chat`) works through Vercel's
  proxy and Render's HTTP server.
- Session state is in-memory (design doc §5.7); a single backend instance is
  fine for the demo. Move to Redis before scaling horizontally.
- The RAG index and eval DB live on the backend's local disk. On Render's free
  tier disk is ephemeral — rebuild the Chroma index on deploy, or attach a disk.
