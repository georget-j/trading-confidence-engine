"""Shared helpers for risk calculators.

Conventions used across all VaR methods:
- Returns are simple daily returns (decimal), not log returns.
- VaR and CVaR are reported as POSITIVE loss numbers in dollars.
- Horizon scaling uses sqrt(T) on volatility (standard assumption — caveated
  by the V5 limitations text).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def to_returns_array(returns: list[float]) -> npt.NDArray[np.float64]:
    """Validate and convert a returns list to a numpy array.

    Raises ValueError on insufficient data or non-finite values.
    """
    arr = np.asarray(returns, dtype=np.float64)
    if arr.size < 30:
        raise ValueError(f"Need at least 30 return observations, got {arr.size}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("Returns contain NaN or infinite values")
    return arr


def horizon_scale(volatility: float, horizon_days: int) -> float:
    """Scale a daily volatility to a multi-day horizon via sqrt(T)."""
    return float(volatility * np.sqrt(horizon_days))


def horizon_scale_mean(mean: float, horizon_days: int) -> float:
    """Scale a daily mean to a multi-day horizon linearly."""
    return float(mean * horizon_days)
