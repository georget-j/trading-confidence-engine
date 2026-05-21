# Trading Confidence Engine

A high-confidence AI-assisted trading calculation engine. LLMs propose; deterministic numerical methods verify.

> **Core rule:** LLM confidence is never truth. Final numbers come from independent deterministic calculators that agree within tolerance. Every answer carries a `verification_status` and a full audit trail.

## Status

- **V0** — Skeleton: typed schemas, stub pipeline, end-to-end audit log.
- **V1** — Options pricing: py_vollib (closed-form) + QuantLib (binomial) cross-verified.

See [`/Users/admin/.claude/plans/hey-claude-i-want-partitioned-donut.md`](../.claude/plans/hey-claude-i-want-partitioned-donut.md) for the full V0–V10 roadmap.

## Layout

```
apps/api/       FastAPI backend (Python 3.12, uv-managed)
apps/web/       Next.js 15 frontend
packages/       Shared types
benchmarks/     Immutable test sets, golden numbers
infra/          Deploy configs
```

## Quickstart

```bash
# Backend
cd apps/api
uv sync
uv run pytest
uv run uvicorn src.api.main:app --reload

# Frontend
cd apps/web
pnpm install
pnpm dev
```

## LLM setup (optional — needed only for chat input)

The structured form (`/calc/options/price`) works without an LLM. The chat
input (`/chat/parse`, `/chat/price`) needs a provider key.

1. Copy the template into a gitignored `.env`:

   ```bash
   cp apps/api/env.example apps/api/.env
   ```

2. Open `apps/api/.env` and uncomment + fill in **one** provider:
   - Anthropic (default model `anthropic/claude-haiku-4-5-20251001`):
     `ANTHROPIC_API_KEY=sk-ant-...`
   - OpenAI (set `LLM_MODEL=openai/gpt-4o-mini`):
     `OPENAI_API_KEY=sk-proj-...`

3. Restart the API (`make api`). `apps/api/.env` is loaded automatically.

**Never commit `.env`.** It is gitignored. If you accidentally paste a key
into a chat, terminal output, or commit, treat it as compromised and rotate it
at the provider's dashboard.

## Verification status meanings

| Status               | Meaning                                                               |
| -------------------- | --------------------------------------------------------------------- |
| `verified`           | ≥2 independent methods agree within tolerance AND all invariants pass |
| `partially_verified` | One method only, or bounds pass but agreement is borderline           |
| `not_verified`       | Methods disagree, invariants violated, or unsupported calc family     |

**Not investment advice.** This is a calculation engine, not a recommendation system.
