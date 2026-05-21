"""Shared helpers for portfolio optimization.

Conventions:
- `returns_matrix` is (T, N): T days of returns for N assets in column order.
- Mean and covariance are computed in DAILY units, then annualised by 252
  trading days when reporting to the user.
- All weights are non-negative and sum to 1 (long-only, fully invested).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

TRADING_DAYS = 252


def returns_stats(
    returns_matrix: npt.NDArray[np.float64],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Return (annualised mean vector, annualised covariance matrix)."""
    mu_daily = returns_matrix.mean(axis=0)
    cov_daily = np.cov(returns_matrix, rowvar=False, ddof=1)
    return mu_daily * TRADING_DAYS, cov_daily * TRADING_DAYS


def portfolio_volatility(
    weights: npt.NDArray[np.float64], cov: npt.NDArray[np.float64]
) -> float:
    return float(np.sqrt(weights @ cov @ weights))


def portfolio_return(
    weights: npt.NDArray[np.float64], mu: npt.NDArray[np.float64]
) -> float:
    return float(weights @ mu)


def risk_contributions(
    weights: npt.NDArray[np.float64], cov: npt.NDArray[np.float64]
) -> npt.NDArray[np.float64]:
    """Per-asset share of total portfolio variance. Sums to 1."""
    portfolio_var = float(weights @ cov @ weights)
    if portfolio_var <= 0:
        # Degenerate (zero-vol) portfolio — distribute equally to avoid
        # divide-by-zero. The caller's invariant check will catch this.
        return np.full_like(weights, 1.0 / weights.size)
    marginal = cov @ weights
    return weights * marginal / portfolio_var
