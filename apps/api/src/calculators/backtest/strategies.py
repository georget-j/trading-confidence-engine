"""Strategy signal generators.

Each returns a `positions` array of length T, where positions[t] ∈ [0, 1]
is the fraction of capital invested AT THE START OF DAY t (i.e. the
position that will earn return[t]). Long-only, no leverage.

The critical contract: positions[t] may only use information from
returns[:t] (strictly before day t). Anything else is a look-ahead bug,
which our detector tests for explicitly.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def buy_and_hold(returns: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Always fully invested from day 0."""
    return np.ones_like(returns)


def ma_crossover(
    returns: npt.NDArray[np.float64], fast: int, slow: int
) -> npt.NDArray[np.float64]:
    """Long when fast SMA > slow SMA, flat otherwise.

    SMAs are computed over PAST returns only — positions[t] uses returns[:t].
    """
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be < slow ({slow})")
    t = returns.size
    positions = np.zeros_like(returns)
    cum = np.cumsum(returns)
    for i in range(slow, t):
        # Mean over [i-fast, i) and [i-slow, i) — strictly past.
        fast_mean = (cum[i - 1] - cum[i - 1 - fast]) / fast
        slow_mean = (cum[i - 1] - cum[i - 1 - slow]) / slow
        positions[i] = 1.0 if fast_mean > slow_mean else 0.0
    return positions


def momentum(
    returns: npt.NDArray[np.float64], lookback: int
) -> npt.NDArray[np.float64]:
    """Long when trailing-`lookback` cumulative return is positive."""
    t = returns.size
    positions = np.zeros_like(returns)
    cum = np.cumsum(returns)
    for i in range(lookback, t):
        # Sum of returns over [i-lookback, i) — strictly past.
        trailing = cum[i - 1] - cum[i - 1 - lookback]
        positions[i] = 1.0 if trailing > 0 else 0.0
    return positions
