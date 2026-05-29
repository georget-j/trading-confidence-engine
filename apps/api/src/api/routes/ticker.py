"""Ticker info + options-chain endpoints — backs Phase 7's Trade Ideas tab.

Two endpoints:

- ``GET /api/ticker/{ticker}/summary`` — spot + realised vol + sector + cap.
- ``GET /api/ticker/{ticker}/chain?expiry=YYYY-MM-DD`` — full options chain
  for one expiry. ``GET /api/ticker/{ticker}/expiries`` lists the available
  ``expiry`` values.

The provider is injected via FastAPI's dependency-injection — tests pass a
deterministic fake so the suite doesn't hit yfinance.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.data_providers.market_data import MarketDataError
from src.data_providers.ticker_info import (
    OptionsChain,
    TickerInfoProvider,
    TickerSummary,
    default_ticker_info_provider,
)

router = APIRouter()


# ---- Wire-level schemas -----------------------------------------------------


class TickerSummaryModel(BaseModel):
    ticker: str
    spot: float
    spot_currency: str
    realised_vol_annualised: float = Field(
        ...,
        description="Annualised stdev of the last ~30 daily returns.",
    )
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    short_name: str | None = None
    long_name: str | None = None


class OptionChainEntryModel(BaseModel):
    contract_symbol: str
    option_type: str
    strike: float
    last_price: float | None = None
    bid: float | None = None
    ask: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    in_the_money: bool


class OptionsChainModel(BaseModel):
    ticker: str
    expiry: str
    spot: float
    entries: list[OptionChainEntryModel]


class ExpiriesModel(BaseModel):
    ticker: str
    expiries: list[str]


# ---- Dependency injection ---------------------------------------------------


def _provider() -> TickerInfoProvider:
    """FastAPI dependency — overridable in tests via
    ``app.dependency_overrides[_provider] = lambda: fake_provider``.
    """
    return default_ticker_info_provider()


ProviderDep = Annotated[TickerInfoProvider, Depends(_provider)]


# ---- Endpoints --------------------------------------------------------------


@router.get("/{ticker}/summary", response_model=TickerSummaryModel)
def get_summary(
    ticker: str,
    provider: ProviderDep,
) -> TickerSummaryModel:
    if not ticker.strip():
        raise HTTPException(status_code=422, detail="ticker must not be empty")
    try:
        summary = provider.fetch_ticker_summary(ticker)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _summary_to_model(summary)


@router.get("/{ticker}/expiries", response_model=ExpiriesModel)
def list_expiries(
    ticker: str,
    provider: ProviderDep,
) -> ExpiriesModel:
    if not ticker.strip():
        raise HTTPException(status_code=422, detail="ticker must not be empty")
    try:
        expiries = provider.list_expiries(ticker)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ExpiriesModel(ticker=ticker.upper().strip(), expiries=expiries)


@router.get("/{ticker}/chain", response_model=OptionsChainModel)
def get_options_chain(
    ticker: str,
    provider: ProviderDep,
    expiry: str = Query(..., description="Expiry as ISO YYYY-MM-DD"),
) -> OptionsChainModel:
    if not ticker.strip():
        raise HTTPException(status_code=422, detail="ticker must not be empty")
    try:
        chain = provider.fetch_options_chain(ticker, expiry)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _chain_to_model(chain)


# ---- Mappers ----------------------------------------------------------------


def _summary_to_model(s: TickerSummary) -> TickerSummaryModel:
    return TickerSummaryModel(
        ticker=s.ticker,
        spot=s.spot,
        spot_currency=s.spot_currency,
        realised_vol_annualised=s.realised_vol_annualised,
        sector=s.sector,
        industry=s.industry,
        market_cap=s.market_cap,
        short_name=s.short_name,
        long_name=s.long_name,
    )


def _chain_to_model(c: OptionsChain) -> OptionsChainModel:
    return OptionsChainModel(
        ticker=c.ticker,
        expiry=c.expiry,
        spot=c.spot,
        entries=[
            OptionChainEntryModel(
                contract_symbol=e.contract_symbol,
                option_type=e.option_type,
                strike=e.strike,
                last_price=e.last_price,
                bid=e.bid,
                ask=e.ask,
                volume=e.volume,
                open_interest=e.open_interest,
                implied_volatility=e.implied_volatility,
                in_the_money=e.in_the_money,
            )
            for e in c.entries
        ],
    )
