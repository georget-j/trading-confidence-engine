"""FastAPI application entry point."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load apps/api/.env if present. Real env vars always win over the .env file,
# so production deploys (Railway/Fly) inject secrets normally.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

from src.api.routes import chat as chat_routes  # noqa: E402  (after load_dotenv)
from src.api.routes import options as options_routes  # noqa: E402
from src.api.routes import portfolio as portfolio_routes  # noqa: E402
from src.api.routes import risk as risk_routes  # noqa: E402

app = FastAPI(
    title="Trading Confidence Engine",
    description=(
        "High-confidence trading calculation engine. LLMs propose; "
        "deterministic methods verify. Every answer carries a verification status."
    ),
    version="0.1.0",
)

# CORS for the Next.js dev frontend. Tighten in production by setting
# CORS_ALLOWED_ORIGINS to a comma-separated list of permitted origins.
_default_origins = (
    "http://localhost:3000,http://localhost:3001,"
    "http://127.0.0.1:3000,http://127.0.0.1:3001"
)
_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(options_routes.router, prefix="/calc/options", tags=["options"])
app.include_router(risk_routes.router, prefix="/calc/risk", tags=["risk"])
app.include_router(
    portfolio_routes.router, prefix="/calc/portfolio", tags=["portfolio"]
)
app.include_router(chat_routes.router, prefix="/chat", tags=["chat"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
