# Deploying Trading Confidence Engine

Two-service deploy: **Next.js web app on Vercel**, **FastAPI backend on Railway**.

```
 ┌─────────────────┐         ┌──────────────────┐
 │ Vercel          │  HTTPS  │ Railway          │
 │ (Next.js, web)  │ ──────► │ (FastAPI, api)   │
 └─────────────────┘         └──────────────────┘
        ▲                            │
        │                            ▼
   browser visits              yfinance / LiteLLM
   the Vercel URL              (Anthropic or OpenAI)
```

The web app reads `NEXT_PUBLIC_API_BASE` at build time and calls the
Railway-hosted API directly from the browser. The API permits the Vercel
origin via `CORS_ALLOWED_ORIGINS`.

---

## 1. Deploy the API on Railway

The repo includes a `Dockerfile` + `railway.json` in `apps/api/`. Railway
auto-detects them.

### 1a. Create the project

1. Sign in at [railway.com](https://railway.com).
2. **New Project → Deploy from GitHub repo** → pick this repository.
3. When Railway prompts for the service root, set it to **`apps/api`**.
   (Railway calls this "Root Directory" — it's the path the Dockerfile builds
   from.)
4. Railway sees `railway.json` and uses the Dockerfile builder automatically.

### 1b. Set environment variables (Service → Variables tab)

Required:

| Variable                                  | Value                                                             | Why                                                                                          |
| ----------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `LLM_MODEL`                               | `anthropic/claude-haiku-4-5-20251001` (or OpenAI equivalent)      | Picks the LLM provider for chat parsing.                                                     |
| `ANTHROPIC_API_KEY` _or_ `OPENAI_API_KEY` | your key                                                          | Must match the provider in `LLM_MODEL`.                                                      |
| `CORS_ALLOWED_ORIGINS`                    | `https://YOUR-PROJECT.vercel.app` (comma-separated for multiples) | Restricts which origins can call the API. Fill in once you know the Vercel URL — see step 2. |

Optional:

| Variable        | Default             | Why                                                                       |
| --------------- | ------------------- | ------------------------------------------------------------------------- |
| `LLM_TIMEOUT_S` | `15`                | Per-request LLM timeout.                                                  |
| `PORT`          | injected by Railway | The Dockerfile reads `${PORT}`; Railway provides it. Do not set manually. |

### 1c. Generate a public URL

Service → **Settings → Networking → Generate Domain**. Railway returns
something like `https://tce-api-production.up.railway.app`.

Test it: `curl https://YOUR-RAILWAY-URL/health` → `{"status":"ok"}`.

---

## 2. Deploy the web app on Vercel

### 2a. Import the repo

1. Sign in at [vercel.com](https://vercel.com).
2. **Add New… → Project** → import the GitHub repo.
3. **Root Directory:** set to **`apps/web`** (Vercel needs this because the
   project is in a monorepo).
4. Framework Preset: **Next.js** (auto-detected).
5. Build/Output settings: leave defaults.

### 2b. Set environment variables (Settings → Environment Variables)

| Variable               | Scope                | Value                                          |
| ---------------------- | -------------------- | ---------------------------------------------- |
| `NEXT_PUBLIC_API_BASE` | Production + Preview | `https://YOUR-RAILWAY-URL` (no trailing slash) |

The `NEXT_PUBLIC_` prefix is required — Next.js only exposes
`NEXT_PUBLIC_*` vars to client-side JS, and the API base is read from the
browser.

### 2c. Deploy

Click **Deploy**. First build takes ~2 minutes (most of it is
`next build` static-prerendering the single page).

### 2d. Wire CORS

Once Vercel gives you the production URL, go back to **Railway → API service
→ Variables** and set:

```
CORS_ALLOWED_ORIGINS=https://YOUR-PROJECT.vercel.app
```

(Include any preview-branch URLs too if you want previews to talk to prod
API. Or set up a separate Railway preview service for full isolation.)

Railway will redeploy automatically on env change.

---

## 3. Verify end-to-end

1. Open `https://YOUR-PROJECT.vercel.app`.
2. Options tab → click **Walk me through it** in the tutorial panel. The
   worked example uses a baked fixture (no API call), so this confirms the
   web app rendered.
3. Risk tab → enter ticker `SPY`, hit **Compute VaR**. This calls the API.
   You should get a result back. If you see a CORS error in the console,
   the `CORS_ALLOWED_ORIGINS` value doesn't match the Vercel origin exactly.
4. Options tab → type into the chat box. This exercises the LLM round-trip
   and confirms the API key is set on Railway.

---

## Local development still works unchanged

```
# Terminal 1 — API
cd apps/api
uv run uvicorn src.api.main:app --reload

# Terminal 2 — Web
cd apps/web
pnpm dev
```

`NEXT_PUBLIC_API_BASE` defaults to `http://localhost:8000` when unset, so no
`.env.local` is needed for local dev.

To point the local web app at the deployed API instead, create
`apps/web/.env.local` containing:

```
NEXT_PUBLIC_API_BASE=https://YOUR-RAILWAY-URL
```

`.env.local` is gitignored.

---

## Cost notes

- **Vercel Hobby:** free for personal/portfolio use. Next.js static-prerendered
  page costs essentially nothing.
- **Railway:** ~$5/mo trial credit, then pay-as-you-go. Idle FastAPI service
  with QuantLib/cvxpy in memory is ~256MB RAM = a few dollars a month if
  pinged occasionally. Sleeps eligible if you opt in.
- **LLM:** Anthropic Haiku 4.5 is the default — pennies per session for chat
  parsing.

---

## Troubleshooting

**"CORS policy: No 'Access-Control-Allow-Origin'"** — Vercel URL not in
`CORS_ALLOWED_ORIGINS` on Railway. Set it exactly (no trailing slash,
include `https://`).

**"API 500: …"** — Check Railway logs (Deployments → Logs). LLM key missing
or `LLM_MODEL` mismatched with the key provider is the most common cause.

**Vercel build fails with TypeScript errors** — run `pnpm typecheck` locally
from `apps/web`. Vercel will not silently swallow TS errors.

**Railway image build fails on QuantLib / cvxpy** — these have manylinux
wheels for cp312, but the wheel is large. If you see a timeout, increase
Railway's build timeout in Settings → Build.

**Health check failing** — Railway expects `/health` to return 200 within 30
seconds. Cold-start is usually <5s; if it's longer, your LLM router is
making a synchronous outbound call at import time. The current code does
not — it lazy-inits — so this should not happen.
