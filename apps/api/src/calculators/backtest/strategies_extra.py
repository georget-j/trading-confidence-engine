"""Additional strategies — mean reversion and Bollinger Bands.

Same contract as `strategies.py`:
- Each returns a `positions` array of length T.
- positions[t] ∈ {0, 1} (long-only, fully invested when long).
- positions[t] may only depend on returns[:t] — strict past, no look-ahead.

Both strategies operate on the synthetic price series `P_t = exp(cumsum(returns))`
so that we can compute z-scores / Bollinger bands without needing the raw
price level (which the runner doesn't have access to here).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def _prices_from_returns(
    returns: npt.NDArray[np.float64], *, P0: float = 1.0  # noqa: N803
) -> npt.NDArray[np.float64]:
    """Reconstruct a price index from a returns series.

    P_t = P0 * Π (1 + r_i) for i = 1..t. Anchored at P_0 = 1 by default —
    only relative levels matter for z-scores and Bollinger calculations.
    """
    return (P0 * np.cumprod(1.0 + returns)).astype(np.float64)


def mean_reversion(
    returns: npt.NDArray[np.float64],
    lookback: int,
    entry_z: float,
) -> npt.NDArray[np.float64]:
    """Z-score mean reversion (long-only).

    Logic:
      * Compute a rolling mean μ_t and stdev σ_t from prices[t-lookback : t].
      * z_t = (price[t] − μ_t) / σ_t.
      * If z_t < −entry_z → go long (positions[t] = 1).
      * If z_t > 0       → exit (positions[t] = 0). Symmetric one-sided exit at
                          the mean, NOT the upper band — keeps it long-only.

    All decisions at time t use information strictly from prior days
    (returns[:t] → prices[:t]).
    """
    t = returns.size
    prices = _prices_from_returns(returns)
    positions = np.zeros_like(returns)

    for i in range(lookback, t):
        # Window: prices[i - lookback : i] — strictly past.
        window = prices[i - lookback : i]
        mu = float(window.mean())
        sigma = float(window.std(ddof=1))
        if sigma <= 0:
            positions[i] = positions[i - 1]
            continue
        z = (float(prices[i - 1]) - mu) / sigma
        prev = positions[i - 1]
        if prev == 0 and z < -entry_z:
            positions[i] = 1.0
        elif prev == 1 and z > 0.0:
            positions[i] = 0.0
        else:
            positions[i] = prev
    return positions


def bollinger(
    returns: npt.NDArray[np.float64],
    lookback: int,
    mult: float,
) -> npt.NDArray[np.float64]:
    """Bollinger Band mean reversion (long-only).

    Logic:
      * Rolling mean μ_t, stdev σ_t over prices[t-lookback : t].
      * Lower band = μ_t − mult·σ_t.
      * Long when price[t] < lower band; exit when price[t] crosses back above μ_t.

    Long-only: short band signal is not used (would mirror the long side but
    pulls the strategy below 0 weight, which the backtest engine doesn't
    support). All decisions use strictly past data.
    """
    t = returns.size
    prices = _prices_from_returns(returns)
    positions = np.zeros_like(returns)

    for i in range(lookback, t):
        window = prices[i - lookback : i]
        mu = float(window.mean())
        sigma = float(window.std(ddof=1))
        if sigma <= 0:
            positions[i] = positions[i - 1]
            continue
        lower = mu - mult * sigma
        p_prev = float(prices[i - 1])
        prev = positions[i - 1]
        if prev == 0 and p_prev < lower:
            positions[i] = 1.0
        elif prev == 1 and p_prev > mu:
            positions[i] = 0.0
        else:
            positions[i] = prev
    return positions
