"""Price history route — used by the in-app chart.

In-memory TTL cache (60s) so the UI's auto-refresh doesn't hammer yfinance.
A production setup would use Redis; for V8.x this is fine.
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from src.data_providers import default_provider
from src.data_providers.market_data import MarketDataError

router = APIRouter()

_CACHE_TTL_S = 60.0
_cache: dict[tuple[str, int], tuple[float, list[tuple[str, float]]]] = {}


class PricePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: str
    close: float


class PriceHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    points: list[PricePoint]
    cached: bool


@router.get("/history", response_model=PriceHistoryResponse)
def history(
    ticker: Annotated[str, Query(min_length=1, max_length=10)],
    days: Annotated[int, Query(ge=5, le=2520)] = 60,
) -> PriceHistoryResponse:
    """Daily close prices for a ticker over the last `days` trading days."""
    key = (ticker.upper(), days)
    now = time.time()
    hit = _cache.get(key)
    if hit and (now - hit[0]) < _CACHE_TTL_S:
        return PriceHistoryResponse(
            ticker=key[0],
            points=[PricePoint(date=d, close=c) for d, c in hit[1]],
            cached=True,
        )

    try:
        pairs = default_provider().fetch_price_history(key[0], days)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"Price fetch failed: {type(exc).__name__}"
        ) from exc

    _cache[key] = (now, pairs)
    return PriceHistoryResponse(
        ticker=key[0],
        points=[PricePoint(date=d, close=c) for d, c in pairs],
        cached=False,
    )
