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

## Verification status meanings

| Status               | Meaning                                                               |
| -------------------- | --------------------------------------------------------------------- |
| `verified`           | ≥2 independent methods agree within tolerance AND all invariants pass |
| `partially_verified` | One method only, or bounds pass but agreement is borderline           |
| `not_verified`       | Methods disagree, invariants violated, or unsupported calc family     |

**Not investment advice.** This is a calculation engine, not a recommendation system.
