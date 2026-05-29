"""Peer comparison endpoint (Phase 7e).

``GET /api/compare/{ticker}/peers`` — return ranked similar-sentiment peers
for a reference ticker.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.trader_schemas import PeerComparisonResponse
from src.data_providers.market_data import (
    MarketDataError,
    MarketDataProvider,
    default_provider,
)
from src.data_providers.ticker_info import (
    TickerInfoProvider,
    default_ticker_info_provider,
)
from src.orchestration.peer_finder import find_peers

router = APIRouter()


def _ticker_info_provider() -> TickerInfoProvider:
    return default_ticker_info_provider()


def _market_data_provider() -> MarketDataProvider:
    return default_provider()


TickerInfoDep = Annotated[TickerInfoProvider, Depends(_ticker_info_provider)]
MarketDataDep = Annotated[MarketDataProvider, Depends(_market_data_provider)]


@router.get("/{ticker}/peers", response_model=PeerComparisonResponse)
def get_peers(
    ticker: str,
    ticker_info: TickerInfoDep,
    market_data: MarketDataDep,
    lookback_days: int = Query(126, ge=60, le=2520),
    top_k: int = Query(10, ge=1, le=50),
    min_correlation: float = Query(0.0, ge=-1.0, le=1.0),
    cheaper_only: bool = Query(False, alias="cheaper_than"),
) -> PeerComparisonResponse:
    if not ticker.strip():
        raise HTTPException(status_code=422, detail="ticker must not be empty")
    try:
        return find_peers(
            ticker,
            lookback_days=lookback_days,
            top_k=top_k,
            min_correlation=min_correlation,
            cheaper_than_reference_only=cheaper_only,
            ticker_info_provider=ticker_info,
            market_data_provider=market_data,
        )
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
