"""Imported-portfolio analytics orchestration.

Pure-Python coordinator that takes ``list[Holding]`` and produces
``PortfolioAnalysis`` by fanning out to:

- ``TickerInfoProvider`` for spot + sector per ticker (parallelisable, but
  sequential here — yfinance rate-limits aggressive concurrent fetches and
  Phase 7 portfolios are typically ≤30 tickers)
- ``MarketDataProvider`` for aligned daily returns when ≥2 tickers (used for
  the correlation matrix + portfolio volatility)

No verification engine wiring yet — Phase 7d (Hedge Finder) is where the
backtest pipeline plugs in. This module is the foundation that hedge
finding sits on top of.
"""

from __future__ import annotations

import logging
import math

import numpy as np

from src.core.trader_schemas import (
    ConcentrationAlert,
    CorrelationMatrix,
    Holding,
    PortfolioAnalysis,
    PricedHolding,
    SectorExposure,
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

LOG = logging.getLogger(__name__)

# Concentration alert thresholds — surfaced when crossed.
SINGLE_POSITION_THRESHOLD = 0.25  # any one ticker > 25% of book
SINGLE_SECTOR_THRESHOLD = 0.45    # any one sector > 45% of book


def analyse_portfolio(
    holdings: list[Holding],
    *,
    lookback_days: int = 252,
    ticker_info_provider: TickerInfoProvider | None = None,
    market_data_provider: MarketDataProvider | None = None,
) -> PortfolioAnalysis:
    """Run the full analytics pipeline on a list of holdings."""
    ticker_info = ticker_info_provider or default_ticker_info_provider()
    market_data = market_data_provider or default_provider()

    if not holdings:
        raise ValueError("analyse_portfolio called with no holdings")

    # Step 1: price every holding + pull sector from the ticker provider.
    priced, limitations = _price_holdings(holdings, ticker_info)
    total_value = sum(p.value_usd for p in priced)
    if total_value <= 0:
        raise MarketDataError(
            "Total portfolio value is zero — at least one holding must price."
        )

    # Compute weights now that we have the total.
    priced = [
        p.model_copy(update={"weight": p.value_usd / total_value}) for p in priced
    ]

    # Step 2: sector exposure (group by sector, "Unknown" bucket for nulls).
    sector_exposure = _bucket_by_sector(priced)

    # Step 3: concentration alerts.
    alerts = _concentration_alerts(priced, sector_exposure)

    # Step 4: correlation matrix + portfolio vol (skip when insufficient).
    correlation: CorrelationMatrix | None = None
    portfolio_vol: float | None = None
    if len(priced) >= 2:
        try:
            correlation, portfolio_vol = _correlation_and_vol(
                priced,
                lookback_days=lookback_days,
                market_data=market_data,
            )
        except MarketDataError as exc:
            limitations.append(
                "Correlation matrix unavailable: " + str(exc)
            )

    return PortfolioAnalysis(
        total_value_usd=total_value,
        holdings=priced,
        sector_exposure=sector_exposure,
        concentration_alerts=alerts,
        portfolio_volatility_annualised=portfolio_vol,
        correlation_matrix=correlation,
        lookback_days=lookback_days,
        limitations=limitations,
    )


def _price_holdings(
    holdings: list[Holding],
    ticker_info: TickerInfoProvider,
) -> tuple[list[PricedHolding], list[str]]:
    out: list[PricedHolding] = []
    limitations: list[str] = []
    for h in holdings:
        try:
            summary = ticker_info.fetch_ticker_summary(h.ticker)
        except MarketDataError as exc:
            limitations.append(
                f"{h.ticker}: priced as zero — {exc}"
            )
            # Still surface the holding so the user sees the failure context.
            out.append(
                PricedHolding(
                    ticker=h.ticker,
                    shares=h.shares,
                    cost_basis=h.cost_basis,
                    currency=h.currency,
                    spot=0.0,
                    value_usd=0.0,
                    weight=0.0,
                    sector=None,
                    industry=None,
                    pnl_usd=None,
                )
            )
            continue
        value = float(h.shares) * float(summary.spot)
        pnl: float | None = None
        if h.cost_basis is not None:
            pnl = (summary.spot - h.cost_basis) * h.shares
        out.append(
            PricedHolding(
                ticker=summary.ticker,
                shares=h.shares,
                cost_basis=h.cost_basis,
                currency=h.currency or summary.spot_currency,
                spot=summary.spot,
                value_usd=value,
                weight=0.0,  # filled in by caller once total is known
                sector=summary.sector,
                industry=summary.industry,
                pnl_usd=pnl,
            )
        )
    return out, limitations


def _bucket_by_sector(priced: list[PricedHolding]) -> list[SectorExposure]:
    totals: dict[str, float] = {}
    for p in priced:
        key = p.sector or "Unknown"
        totals[key] = totals.get(key, 0.0) + p.value_usd
    grand = sum(totals.values()) or 1.0
    out = [
        SectorExposure(sector=k, value_usd=v, weight=v / grand)
        for k, v in totals.items()
    ]
    out.sort(key=lambda s: -s.value_usd)
    return out


def _concentration_alerts(
    priced: list[PricedHolding],
    sector_exposure: list[SectorExposure],
) -> list[ConcentrationAlert]:
    alerts: list[ConcentrationAlert] = []
    for p in priced:
        if p.weight > SINGLE_POSITION_THRESHOLD:
            alerts.append(
                ConcentrationAlert(
                    kind="single_position",
                    label=p.ticker,
                    weight=p.weight,
                    threshold=SINGLE_POSITION_THRESHOLD,
                    message=(
                        f"{p.ticker} is {p.weight * 100:.1f}% of the portfolio — "
                        f"above the {SINGLE_POSITION_THRESHOLD * 100:.0f}% single-position alert threshold."
                    ),
                )
            )
    for s in sector_exposure:
        if s.weight > SINGLE_SECTOR_THRESHOLD:
            alerts.append(
                ConcentrationAlert(
                    kind="single_sector",
                    label=s.sector,
                    weight=s.weight,
                    threshold=SINGLE_SECTOR_THRESHOLD,
                    message=(
                        f"{s.sector} sector is {s.weight * 100:.1f}% of the portfolio — "
                        f"above the {SINGLE_SECTOR_THRESHOLD * 100:.0f}% single-sector alert threshold. "
                        f"Hedge Finder can suggest anti-correlated alternatives."
                    ),
                )
            )
    return alerts


def _correlation_and_vol(
    priced: list[PricedHolding],
    *,
    lookback_days: int,
    market_data: MarketDataProvider,
) -> tuple[CorrelationMatrix, float]:
    # Only include holdings that priced successfully — others would corrupt
    # the correlation matrix with zero-return rows.
    active = [p for p in priced if p.value_usd > 0]
    if len(active) < 2:
        raise MarketDataError(
            "Need at least 2 priced holdings to compute correlation"
        )
    tickers = [p.ticker for p in active]
    aligned_tickers, returns_nested = market_data.fetch_aligned_returns(
        tickers, lookback_days
    )
    returns = np.asarray(returns_nested, dtype=np.float64)  # shape (T, N)
    if returns.ndim != 2 or returns.shape[1] != len(aligned_tickers):
        raise MarketDataError(
            f"Provider returned an unexpectedly shaped matrix: {returns.shape}"
        )
    # Correlation matrix (Pearson). Use rowvar=False since rows are days.
    # `corrcoef` returns a scalar when N=1, but the guard above ensures
    # N >= 2, so the result is always a 2-D ndarray.
    corr = np.asarray(np.corrcoef(returns, rowvar=False))
    # Re-order to match `tickers` (provider may have reshuffled).
    idx = [aligned_tickers.index(t) for t in tickers]
    corr = corr[np.ix_(idx, idx)]
    # NaN cleanup (rare — flat-return columns would yield NaN).
    corr = np.where(np.isfinite(corr), corr, 0.0)
    np.fill_diagonal(corr, 1.0)

    # Portfolio volatility: w^T Σ w, scaled to annual.
    weight_vec = np.array(
        [p.weight for p in active], dtype=np.float64
    )
    # Re-normalise weights against just the active subset (the rest are 0).
    weight_vec = weight_vec / weight_vec.sum() if weight_vec.sum() > 0 else weight_vec
    cov = np.cov(returns, rowvar=False, ddof=1)
    cov = cov[np.ix_(idx, idx)]
    daily_var = float(weight_vec @ cov @ weight_vec)
    portfolio_vol = math.sqrt(max(daily_var, 0.0) * 252.0)

    matrix_payload = CorrelationMatrix(
        tickers=tickers,
        matrix=corr.tolist(),
    )
    return matrix_payload, portfolio_vol
