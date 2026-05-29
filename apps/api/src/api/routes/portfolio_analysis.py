"""Portfolio import + analysis endpoints (Phase 7 My Portfolio tab).

- ``POST /api/portfolio/import`` — parse a CSV body OR accept structured
  holdings; returns a normalised ``ImportedPortfolio``.
- ``POST /api/portfolio/analyse`` — given holdings, return a full
  ``PortfolioAnalysis`` (priced holdings, sector breakdown, concentration
  alerts, correlation matrix, portfolio vol).

Provider dependencies are injected via FastAPI so the test suite can drop
in deterministic fakes without touching yfinance.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.core.trader_schemas import (
    Holding,
    ImportedPortfolio,
    PortfolioAnalyseRequest,
    PortfolioAnalysis,
    PortfolioImportRequest,
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
from src.orchestration.portfolio_analysis import analyse_portfolio
from src.parser.portfolio_csv import (
    CSVParseError,
    parse_generic,
    parse_trading212,
)

router = APIRouter()


# ---- Dependency injection ---------------------------------------------------


def _ticker_info_provider() -> TickerInfoProvider:
    return default_ticker_info_provider()


def _market_data_provider() -> MarketDataProvider:
    return default_provider()


TickerInfoDep = Annotated[TickerInfoProvider, Depends(_ticker_info_provider)]
MarketDataDep = Annotated[MarketDataProvider, Depends(_market_data_provider)]


# ---- Endpoints --------------------------------------------------------------


@router.post("/import", response_model=ImportedPortfolio)
def import_portfolio(req: PortfolioImportRequest) -> ImportedPortfolio:
    """Normalise a CSV body or raw holdings list into ``ImportedPortfolio``."""
    if req.holdings is not None and req.csv_text is not None:
        raise HTTPException(
            status_code=422,
            detail="Provide either csv_text or holdings, not both",
        )

    if req.holdings is not None:
        if not req.holdings:
            raise HTTPException(
                status_code=422, detail="holdings list is empty"
            )
        return ImportedPortfolio(
            holdings=req.holdings,
            source="paste",
            rows_seen=len(req.holdings),
        )

    if req.csv_text is None:
        raise HTTPException(
            status_code=422,
            detail="One of csv_text or holdings must be provided",
        )

    source = req.source.strip().lower() or "trading_212"
    parser = parse_trading212 if source == "trading_212" else parse_generic
    try:
        parsed = parser(req.csv_text)
    except CSVParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    holdings = [
        Holding(
            ticker=p.ticker,
            shares=p.shares,
            cost_basis=p.cost_basis,
            currency=p.currency,
        )
        for p in parsed
    ]
    return ImportedPortfolio(
        holdings=holdings,
        source=source,
        rows_seen=len(parsed),
    )


@router.post("/analyse", response_model=PortfolioAnalysis)
def analyse(
    req: PortfolioAnalyseRequest,
    ticker_info: TickerInfoDep,
    market_data: MarketDataDep,
) -> PortfolioAnalysis:
    """Run portfolio analytics on the supplied holdings."""
    try:
        analysis = analyse_portfolio(
            list(req.holdings),
            lookback_days=req.lookback_days,
            ticker_info_provider=ticker_info,
            market_data_provider=market_data,
        )
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return analysis
