"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import options as options_routes

app = FastAPI(
    title="Trading Confidence Engine",
    description=(
        "High-confidence trading calculation engine. LLMs propose; "
        "deterministic methods verify. Every answer carries a verification status."
    ),
    version="0.1.0",
)

# CORS for the Next.js dev frontend. Tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(options_routes.router, prefix="/calc/options", tags=["options"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
