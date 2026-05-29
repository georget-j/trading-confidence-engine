# Trading Confidence Engine

> **AI proposes, math verifies.** A trading calculation engine where LLMs only parse intent — every number is produced by independent deterministic methods that cross-check each other, with a tri-state verification status and a full audit trail on every result.

[**Live demo**](https://tce-web-phi.vercel.app/) · [API](https://tce-api-production.up.railway.app/health) · MIT

---

## What it does

A web app that lets a trader explore options, portfolios, hedges, and peer comparisons on **real US-listed tickers**, with every output backed by ≥1 independent calculator method and a click-to-open verification trace.

Four trader workflows plus a power-user surface:

| Tab              | What it does                                                                                                             | Backed by                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------- |
| **Trade Ideas**  | Pick a ticker → live spot + 30-day IV + sector → build a position → verified scenario explorer (spot/vol/time shocks)    | yfinance + 4-method options pricing         |
| **My Portfolio** | Upload Trading 212 CSV or paste shorthand → priced holdings, sector breakdown, concentration alerts, correlation heatmap | yfinance + Pearson correlation              |
| **Hedge Finder** | Scan a bundled universe for anti-correlated baskets per concentrated sector, with regime-shift warnings                  | Universe scan + correlation half-life check |
| **Compare**      | Rank similar-sentiment peers for a reference ticker (with cheaper-but-similar filter)                                    | Universe scan + market-cap filter           |
| **Calculators**  | Direct access to all 5 calculation families + a Methods Lab to invoke any single method with raw inputs                  | The full verification engine                |

Every number across every tab is one click away from a 6-stage verification trace drawer showing data ingestion → per-method calculation → cross-check → invariants → sensitivity → final verdict.

## The verification engine

Every calculation runs through **at least two independent methods** (different math, different libraries) plus **domain invariants** (no-arbitrage bounds, put-call parity, KKT stationarity, walk-forward reproducibility, look-ahead bias detection, etc.) plus **sensitivity analysis** where applicable.

Result: a tri-state status surfaced on every output.

| Status               | Meaning                                                                                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `verified`           | ≥2 methods agree within tolerance AND every invariant passed AND the result is stable under input perturbation                                                                       |
| `partially_verified` | Only one method available, or methods diverge moderately (typically a real signal — e.g. SPY 99% VaR diverges between historical and parametric because real returns have fat tails) |
| `not_verified`       | Methods disagreed badly or an invariant failed — do not rely on the number                                                                                                           |

### The 19 cross-verified methods

| Family                     | Methods                                                                                                                | Library                    |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| **Options pricing**        | BSM closed-form, Leisen-Reimer binomial (801 steps), Monte Carlo GBM (100k antithetic), Crank-Nicolson PDE             | py_vollib, QuantLib, NumPy |
| **VaR / CVaR**             | Historical quantile, Parametric (normal), Monte Carlo, Cornish-Fisher (skew/kurt-adjusted), Bootstrap (1000 resamples) | NumPy                      |
| **Portfolio optimisation** | Mean-variance QP, Max-Sharpe tangent, Risk parity (log-barrier), Min-variance, Inverse-volatility heuristic            | cvxpy + CLARABEL/SCS       |
| **Backtesting**            | Buy-and-hold, MA crossover, Momentum, Mean-reversion (z-score), Bollinger Bands                                        | NumPy (custom engine)      |

The **Methods Lab** tab lets you invoke any one of these with raw inputs, no orchestration — useful for sanity-checking a partially-verified result by hand.

## Tech stack

- **Backend**: FastAPI · Pydantic v2 · Python 3.12 · uv · py_vollib · QuantLib · cvxpy · NumPy · yfinance · LiteLLM (Anthropic + OpenAI)
- **Frontend**: Next.js 16 · React 19 · Tailwind 4 · Recharts · Radix UI
- **Deploy**: Railway (API, Dockerfile) · Vercel (web, prebuilt artifact uploads)
- **Quality bar**: 358 backend tests · `ruff` clean · `mypy --strict` clean · `tsc --noEmit` clean

## Layout

```
apps/api/                  FastAPI backend (Python 3.12, uv-managed)
  src/calculators/         Per-family calculator implementations (19 methods)
  src/verification/        Cross-method checks + invariants + per-method aggregator
  src/orchestration/       Pipelines: options, var, portfolio, backtest, trader (Phase 7)
  src/data_providers/      yfinance MarketData + TickerInfo + bundled universe
  src/api/routes/          FastAPI routers (calc, chat, lab, ticker, portfolio, hedge, compare)
  src/parser/              CSV parsers (Trading 212, generic) + LLM intent parser
  tests/                   358 tests (calculators, orchestration, parsers, routes, properties)

apps/web/                  Next.js 16 frontend
  src/app/                 Next App Router entry
  src/components/          React components (incl. MethodScorecard, VerificationTraceDrawer,
                           DisclaimerGate, TradeIdeas, MyPortfolio, HedgeFinder, Compare)
  src/lib/                 Typed API clients + tutorial fixtures

benchmarks/                Calibration goldens (regenerable via `make calibrate`)
infra/                     Deploy configs
```

## Quickstart (local dev)

```bash
# Backend
cd apps/api
uv sync
uv run pytest            # 358 tests, ~60s
uv run uvicorn src.api.main:app --reload

# Frontend (separate terminal)
cd apps/web
pnpm install
pnpm dev                 # opens http://localhost:3000
```

The frontend talks to the backend via `NEXT_PUBLIC_API_BASE` (defaults to `http://localhost:8000` for local dev).

## LLM setup (optional)

Structured form endpoints (`/calc/options/price`, `/calc/risk/var`, `/calc/portfolio/optimize`, `/calc/backtest/run`, plus all Phase 7 trader endpoints) work without any LLM. Only the chat input boxes (`/chat/parse/{family}`) need a provider key.

```bash
cp apps/api/env.example apps/api/.env
```

Then uncomment **one** provider in `apps/api/.env`:

- Anthropic (default — `LLM_MODEL=anthropic/claude-haiku-4-5-20251001`): `ANTHROPIC_API_KEY=sk-ant-...`
- OpenAI (set `LLM_MODEL=openai/gpt-4o-mini`): `OPENAI_API_KEY=sk-proj-...`

**The LLM never produces numbers.** It only emits structured Pydantic payloads (`OptionsPricingRequest`, `VaRRequest`, etc.); calculators do all the maths. Verification status is decided after the calculators run, on data the LLM never touches.

> Never commit `.env` — it's gitignored. Treat any key pasted into chat/terminals/commits as compromised; rotate it at the provider dashboard.

## Production deployment

- **Web**: Vercel (project `tce-web`, organisation `georget-js-projects`). Deploy via `vercel build --prod && vercel deploy --prebuilt --prod` — uploading a prebuilt artifact skips the build queue.
- **API**: Railway (service `tce-api`, project `tce-api`). Deploy via `railway up --service tce-api`. Configured via [`apps/api/Dockerfile`](apps/api/Dockerfile) + [`apps/api/railway.json`](apps/api/railway.json).
- **CORS**: `CORS_ALLOWED_ORIGINS` on Railway must include the Vercel production URL; defaults cover localhost dev.
- **`NEXT_PUBLIC_API_BASE`**: must be set on Vercel Production to the Railway API URL. Note: Next.js bakes `NEXT_PUBLIC_*` vars into the bundle at **build time**, so changing this env var requires a full rebuild + redeploy.

## Not investment advice

This is an **educational calculation engine**, not an investment advisor. Nothing here is a personal recommendation. Outputs come from historical data + mathematical models that can — and do — break in new market regimes. Always consult a licensed financial advisor (UK: FCA-authorised; US: SEC/state-registered RIA; EU: MiFID II authorised) before acting on any output. You are responsible for your own trading decisions.

The deployed app enforces a first-visit disclaimer-acceptance gate (`DisclaimerGate.tsx`) and surfaces an "Educational use only" banner on every page. Hedge and peer recommendations carry an additional inline disclaimer noting historical correlations may not hold.

## Differentiators worth knowing about

- **Tri-state verification badge with an audit trail.** No retail competitor publishes "this number was cross-verified by N independent methods within tolerance ε" and lets you click through to see how. The per-method scorecard plus 6-stage trace drawer is the engineering moat.
- **Methods diverge on real fat-tailed data** — and the UI tells you why. Run VaR on `SPY` and you'll get `partially_verified` because historical and parametric disagree; the explanation card calls out fat-tail behaviour explicitly rather than hiding it behind a single number.
- **Per-leg verification on multi-leg options strategies.** Long-call + short-call positions can hide drift inside a near-zero net premium — the strategy verifier requires _every leg_ to agree, not just the aggregate, so verification can't be gamed by cancellation.
- **Anonymous, in-memory only** (Phase 7 design decision). No accounts, no database. Portfolio lives in the browser session; refresh = re-upload. Zero PII surface.

## License

MIT
