"""Hedge finder endpoint (Phase 7d).

``POST /api/hedge/suggest`` — given imported holdings, return ranked
anti-correlated baskets per concentrated sector.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.core.trader_schemas import (
    HedgeSuggestRequest,
    HedgeSuggestResponse,
)
from src.data_providers.market_data import (
    MarketDataError,
    MarketDataProvider,
    default_provider,
)
from src.data_providers.ticker_info import (
    TickerInfoProvider,
    default_ticker_info_provider,
)
from src.orchestration.hedge_finder import suggest_hedges

router = APIRouter()


def _ticker_info_provider() -> TickerInfoProvider:
    return default_ticker_info_provider()


def _market_data_provider() -> MarketDataProvider:
    return default_provider()


TickerInfoDep = Annotated[TickerInfoProvider, Depends(_ticker_info_provider)]
MarketDataDep = Annotated[MarketDataProvider, Depends(_market_data_provider)]


@router.post("/suggest", response_model=HedgeSuggestResponse)
def suggest(
    req: HedgeSuggestRequest,
    ticker_info: TickerInfoDep,
    market_data: MarketDataDep,
) -> HedgeSuggestResponse:
    try:
        suggestions, universe_size, limitations = suggest_hedges(
            list(req.holdings),
            lookback_days=req.lookback_days,
            top_k=req.top_k,
            min_sector_weight=req.min_sector_weight,
            ticker_info_provider=ticker_info,
            market_data_provider=market_data,
        )
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return HedgeSuggestResponse(
        suggestions=suggestions,
        universe_size=universe_size,
        lookback_days=req.lookback_days,
        limitations=limitations,
    )
