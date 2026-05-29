"""Hedge finder — anti-correlated baskets per concentrated sector.

Algorithm:
  1. Price the user's holdings (via ``portfolio_analysis``) → know sector
     weights + total value.
  2. For each sector above ``min_sector_weight``, build a "user basket"
     by aggregating the value-weighted daily returns of the holdings in
     that sector.
  3. Pull daily returns for the bundled universe over the lookback. Drop
     any ticker also present in the user's holdings (you can't hedge a
     thing with itself).
  4. Compute Pearson correlation between each universe ticker's returns
     and the user basket. Return the top-K most negatively correlated.
  5. Also compute trailing 6-month correlation per candidate; flag
     "half_life_warning" when it differs from the full-window value by
     more than 0.30 — surfaces regime-shift risk.

Important caveats:
- The user-basket return series is computed from the SAME `MarketDataProvider`
  fetch as the universe series so the date indexes align by construction.
- We fetch all universe + holding tickers in one provider call to amortise
  the yfinance request and ensure aligned indexes.
"""

from __future__ import annotations

import logging
import math

import numpy as np

from src.core.trader_schemas import (
    HedgeCandidate,
    Holding,
    SectorHedgeSuggestion,
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
from src.data_providers.universe import load_universe

LOG = logging.getLogger(__name__)

# Trailing window used for the half-life warning. ~125 trading days ≈ 6 mo.
RECENT_WINDOW = 125
# How much the recent corr must drift from the full window before warning.
HALF_LIFE_DRIFT = 0.30


def suggest_hedges(
    holdings: list[Holding],
    *,
    lookback_days: int = 504,
    top_k: int = 5,
    min_sector_weight: float = 0.25,
    ticker_info_provider: TickerInfoProvider | None = None,
    market_data_provider: MarketDataProvider | None = None,
) -> tuple[list[SectorHedgeSuggestion], int, list[str]]:
    """Return (suggestions, universe_size_used, limitations)."""
    ticker_info = ticker_info_provider or default_ticker_info_provider()
    market_data = market_data_provider or default_provider()
    universe = load_universe()
    universe_tickers = [u.ticker for u in universe]
    universe_by_ticker = {u.ticker: u for u in universe}

    if not holdings:
        raise ValueError("suggest_hedges called with no holdings")

    limitations: list[str] = []

    # Step 1: price holdings → sector → weight (in USD).
    holding_meta: dict[str, dict[str, float | str]] = {}
    for h in holdings:
        try:
            s = ticker_info.fetch_ticker_summary(h.ticker)
        except MarketDataError as exc:
            limitations.append(f"{h.ticker}: skipped — {exc}")
            continue
        holding_meta[s.ticker] = {
            "shares": h.shares,
            "spot": s.spot,
            "value": s.spot * h.shares,
            "sector": s.sector or "Unknown",
        }

    if not holding_meta:
        raise MarketDataError(
            "All holdings failed to price — cannot build hedge suggestions."
        )

    total_value = sum(float(m["value"]) for m in holding_meta.values())
    if total_value <= 0:
        raise MarketDataError("Total portfolio value is zero.")

    # Step 2: figure out which sectors clear the min weight threshold.
    sector_weights: dict[str, float] = {}
    for m in holding_meta.values():
        sector = str(m["sector"])
        sector_weights[sector] = (
            sector_weights.get(sector, 0.0) + float(m["value"]) / total_value
        )
    target_sectors = {
        s: w for s, w in sector_weights.items()
        if w >= min_sector_weight and s != "Unknown"
    }
    if not target_sectors:
        limitations.append(
            f"No sector exceeds the {min_sector_weight * 100:.0f}% threshold "
            "for hedging — your book is already diversified across sectors."
        )
        return [], len(universe_tickers), limitations

    # Step 3: fetch returns for the union (universe + held tickers in the
    # target sectors) in one provider call so the date index aligns.
    held_tickers_in_targets = [
        t for t, m in holding_meta.items() if m["sector"] in target_sectors
    ]
    # Universe entries that are also in the user's book — exclude from the
    # candidate ranking but still need their returns to build the user basket.
    universe_candidates = [
        t for t in universe_tickers if t not in holding_meta
    ]
    fetch_tickers = sorted(set(universe_candidates + held_tickers_in_targets))

    try:
        aligned, returns_nested = market_data.fetch_aligned_returns(
            fetch_tickers, lookback_days
        )
    except MarketDataError as exc:
        raise MarketDataError(
            f"Hedge finder could not fetch aligned returns: {exc}"
        ) from exc
    returns_matrix = np.asarray(returns_nested, dtype=np.float64)  # (T, M)
    if returns_matrix.ndim != 2 or returns_matrix.shape[1] != len(aligned):
        raise MarketDataError(
            f"Provider returned an unexpectedly shaped matrix: {returns_matrix.shape}"
        )
    col_index = {t: i for i, t in enumerate(aligned)}

    # Step 4: for each target sector, build the user basket and rank candidates.
    out: list[SectorHedgeSuggestion] = []
    for sector, weight in sorted(
        target_sectors.items(), key=lambda kv: -kv[1]
    ):
        # Tickers in this sector that we successfully fetched.
        in_sector = [
            t for t, m in holding_meta.items()
            if m["sector"] == sector and t in col_index
        ]
        if not in_sector:
            limitations.append(
                f"{sector}: no holdings had aligned returns over the lookback."
            )
            continue
        basket_returns = _value_weighted_basket(
            tickers=in_sector,
            value_per_ticker={t: float(holding_meta[t]["value"]) for t in in_sector},
            returns_matrix=returns_matrix,
            col_index=col_index,
        )
        candidates: list[HedgeCandidate] = []
        for cand_ticker in universe_candidates:
            if cand_ticker not in col_index:
                continue
            cand_returns = returns_matrix[:, col_index[cand_ticker]]
            full_corr = _safe_corr(basket_returns, cand_returns)
            if full_corr is None:
                continue
            recent_corr = _safe_corr(
                basket_returns[-RECENT_WINDOW:],
                cand_returns[-RECENT_WINDOW:],
            )
            if recent_corr is None:
                recent_corr = full_corr
            half_life_flag = abs(full_corr - recent_corr) > HALF_LIFE_DRIFT

            meta = universe_by_ticker[cand_ticker]
            candidates.append(
                HedgeCandidate(
                    ticker=cand_ticker,
                    name=meta.name,
                    kind=meta.kind,
                    universe_sector=meta.sector,
                    correlation=full_corr,
                    recent_correlation=recent_corr,
                    half_life_warning=half_life_flag,
                )
            )

        # Rank: most negatively correlated first; tie-break on smaller half-life
        # drift so stable relationships outrank flaky ones at equal correlation.
        candidates.sort(
            key=lambda c: (
                c.correlation,
                abs(c.correlation - c.recent_correlation),
            )
        )
        out.append(
            SectorHedgeSuggestion(
                sector=sector,
                sector_weight=weight,
                candidates=candidates[:top_k],
            )
        )

    return out, len(universe_tickers), limitations


# --- Helpers ---------------------------------------------------------------


def _value_weighted_basket(
    *,
    tickers: list[str],
    value_per_ticker: dict[str, float],
    returns_matrix: np.ndarray,
    col_index: dict[str, int],
) -> np.ndarray:
    """Build the value-weighted daily return series for a sector's holdings."""
    total = sum(value_per_ticker.values()) or 1.0
    series = np.zeros(returns_matrix.shape[0], dtype=np.float64)
    for t in tickers:
        weight = value_per_ticker[t] / total
        series += weight * returns_matrix[:, col_index[t]]
    return series


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float | None:
    """Pearson correlation that returns None instead of NaN on degenerate input."""
    if a.size < 30 or b.size < 30 or a.size != b.size:
        return None
    std_a = float(np.std(a))
    std_b = float(np.std(b))
    if std_a < 1e-12 or std_b < 1e-12:
        return None
    val = float(np.corrcoef(a, b)[0, 1])
    if not math.isfinite(val):
        return None
    return max(-1.0, min(1.0, val))
