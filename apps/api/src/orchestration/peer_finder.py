"""Peer finder — rank similar-sentiment peers for a reference ticker.

Algorithm:
  1. Pull reference ticker summary (sector + industry + market cap + spot).
  2. Build candidate set from the bundled universe, EXCLUDING:
     - The reference itself
     - Any ETF (peers should be operating stocks, not index baskets)
  3. Fetch aligned daily returns for [reference] + candidates.
  4. Compute Pearson correlation between each candidate and the reference.
  5. Optionally restrict to "cheaper-but-similar" — peers with materially
     smaller market cap than the reference but similar return correlation.

We deliberately don't penalise low correlations — the user sees the full
ranking and decides. The frontend defaults to filtering correlation > 0.5
but anything in the universe is shown if the user lowers the threshold.

The peer scan reuses the same provider machinery as the hedge finder so
provider mocks in the test suite work the same way.
"""

from __future__ import annotations

import logging
import math

import numpy as np

from src.core.trader_schemas import PeerCandidate, PeerComparisonResponse
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

# Cap ratio below which a peer counts as "materially cheaper" than reference.
CHEAPER_CAP_RATIO = 0.5


def find_peers(
    reference_ticker: str,
    *,
    lookback_days: int = 126,
    top_k: int = 10,
    min_correlation: float = 0.0,
    cheaper_than_reference_only: bool = False,
    ticker_info_provider: TickerInfoProvider | None = None,
    market_data_provider: MarketDataProvider | None = None,
) -> PeerComparisonResponse:
    ticker_info = ticker_info_provider or default_ticker_info_provider()
    market_data = market_data_provider or default_provider()

    ref_symbol = reference_ticker.strip().upper()
    if not ref_symbol:
        raise ValueError("reference_ticker must not be empty")

    # 1. Reference summary.
    ref_summary = ticker_info.fetch_ticker_summary(ref_symbol)

    # 2. Candidate set — operating stocks only, reference excluded.
    universe = load_universe()
    candidates = [
        u for u in universe if u.kind == "stock" and u.ticker != ref_symbol
    ]
    candidate_tickers = [c.ticker for c in candidates]
    if not candidate_tickers:
        return PeerComparisonResponse(
            reference_ticker=ref_summary.ticker,
            reference_name=ref_summary.long_name or ref_summary.short_name,
            reference_sector=ref_summary.sector,
            reference_industry=ref_summary.industry,
            reference_spot=ref_summary.spot,
            reference_market_cap=ref_summary.market_cap,
            peers=[],
            universe_size=len(universe),
            lookback_days=lookback_days,
            limitations=["Universe has no operating-stock candidates."],
        )

    # 3. Aligned returns for [ref] + candidates.
    fetch_tickers = [ref_symbol] + candidate_tickers
    try:
        aligned, returns_nested = market_data.fetch_aligned_returns(
            fetch_tickers, lookback_days
        )
    except MarketDataError as exc:
        raise MarketDataError(
            f"Peer finder could not fetch aligned returns: {exc}"
        ) from exc
    returns_matrix = np.asarray(returns_nested, dtype=np.float64)  # (T, N)
    if returns_matrix.ndim != 2 or returns_matrix.shape[1] != len(aligned):
        raise MarketDataError(
            f"Provider returned an unexpectedly shaped matrix: {returns_matrix.shape}"
        )
    col_index = {t: i for i, t in enumerate(aligned)}
    if ref_symbol not in col_index:
        raise MarketDataError(
            f"Reference {ref_symbol} returns missing after alignment."
        )
    ref_returns = returns_matrix[:, col_index[ref_symbol]]

    # 4. Correlation per candidate.
    by_ticker = {c.ticker: c for c in candidates}
    out: list[PeerCandidate] = []
    limitations: list[str] = []
    for c in candidates:
        if c.ticker not in col_index:
            continue
        cand_returns = returns_matrix[:, col_index[c.ticker]]
        corr = _safe_corr(ref_returns, cand_returns)
        if corr is None or corr < min_correlation:
            continue
        # Pull spot + cap for the candidate so the UI can render context.
        cand_spot: float | None = None
        cand_cap: float | None = None
        try:
            cand_summary = ticker_info.fetch_ticker_summary(c.ticker)
            cand_spot = cand_summary.spot
            cand_cap = cand_summary.market_cap
        except MarketDataError:
            limitations.append(f"{c.ticker}: summary fetch failed (no spot/cap).")

        is_cheaper = (
            cand_cap is not None
            and ref_summary.market_cap is not None
            and ref_summary.market_cap > 0
            and cand_cap < ref_summary.market_cap * CHEAPER_CAP_RATIO
        )
        same_industry = bool(
            ref_summary.industry
            and by_ticker[c.ticker].sector  # universe.sector is a coarse proxy
            and ref_summary.sector
            and by_ticker[c.ticker].sector == ref_summary.sector
        )
        if cheaper_than_reference_only and not is_cheaper:
            continue
        out.append(
            PeerCandidate(
                ticker=c.ticker,
                name=c.name,
                sector=c.sector,
                kind=c.kind,
                correlation=corr,
                spot=cand_spot,
                market_cap=cand_cap,
                same_industry=same_industry,
                is_cheaper=is_cheaper,
            )
        )

    # 5. Rank: same-industry first, then by correlation desc.
    out.sort(key=lambda p: (-int(p.same_industry), -p.correlation))
    return PeerComparisonResponse(
        reference_ticker=ref_summary.ticker,
        reference_name=ref_summary.long_name or ref_summary.short_name,
        reference_sector=ref_summary.sector,
        reference_industry=ref_summary.industry,
        reference_spot=ref_summary.spot,
        reference_market_cap=ref_summary.market_cap,
        peers=out[:top_k],
        universe_size=len(universe),
        lookback_days=lookback_days,
        limitations=limitations,
    )


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float | None:
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
