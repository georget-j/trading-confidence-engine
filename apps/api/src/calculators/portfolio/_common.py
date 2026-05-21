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
    *,
    shrink_covariance: bool = False,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Return (annualised mean vector, annualised covariance matrix).

    If `shrink_covariance=True`, applies Ledoit-Wolf shrinkage towards the
    constant-correlation prior. This is the standard fix for the fragility
    of sample covariance on short return windows — without it, mean-variance
    over-fits to in-sample noise and concentrates in one asset.
    """
    mu_daily = returns_matrix.mean(axis=0)
    cov_daily = np.cov(returns_matrix, rowvar=False, ddof=1)
    if shrink_covariance:
        cov_daily = _ledoit_wolf_shrink(returns_matrix, cov_daily)
    return mu_daily * TRADING_DAYS, cov_daily * TRADING_DAYS


def _ledoit_wolf_shrink(
    returns: npt.NDArray[np.float64], sample_cov: npt.NDArray[np.float64]
) -> npt.NDArray[np.float64]:
    """Ledoit-Wolf shrinkage towards the constant-correlation target.

    Returns (1 - δ)·sample_cov + δ·target where target shares the sample
    variances on the diagonal but uses the average pairwise correlation
    off-diagonal. δ ∈ [0, 1] is chosen analytically to minimise the expected
    Frobenius distance to the true covariance.

    Reference: Ledoit & Wolf (2004), "Honey, I shrunk the sample covariance
    matrix". scikit-learn ships an equivalent implementation in
    `sklearn.covariance.LedoitWolf` — we implement directly so we can keep
    sklearn as a soft dependency.
    """
    t, n = returns.shape
    if n < 2 or t < 30:
        return sample_cov

    # Constant-correlation target: same diagonal as sample, off-diagonal =
    # average pairwise correlation × sqrt(σ_i σ_j).
    variances = np.diag(sample_cov)
    std = np.sqrt(np.maximum(variances, 0.0))
    # Guard against zero-variance assets (degenerate returns) — they'd cause
    # divide-by-zero in the correlation step.
    if np.any(std <= 0):
        return sample_cov
    corr = sample_cov / np.outer(std, std)
    np.fill_diagonal(corr, 1.0)
    iu = np.triu_indices(n, k=1)
    avg_corr = float(np.mean(corr[iu])) if iu[0].size > 0 else 0.0
    target = avg_corr * np.outer(std, std)
    np.fill_diagonal(target, variances)

    # Shrinkage intensity: derived from the variance of the sample cov entries.
    # Closed-form Ledoit-Wolf estimator (eq. 13 of the 2004 paper, simplified
    # for the constant-correlation target).
    centered = returns - returns.mean(axis=0)
    # π — sum of variances of sample cov entries
    pi_mat = np.zeros((n, n))
    for k in range(t):
        outer = np.outer(centered[k], centered[k])
        pi_mat += (outer - sample_cov) ** 2
    pi_mat /= t
    pi = float(pi_mat.sum())

    # γ — squared Frobenius distance between sample and target
    gamma = float(np.sum((sample_cov - target) ** 2))

    # ρ term — covariance between sample cov entries (approximated via the
    # diagonal contribution, which dominates for constant-correlation target).
    rho_diag = float(np.sum(np.diag(pi_mat)))
    rho = rho_diag  # constant-correlation simplification

    if gamma <= 0:
        return sample_cov
    kappa = (pi - rho) / gamma
    delta = max(0.0, min(1.0, kappa / t))
    shrunk: npt.NDArray[np.float64] = (1 - delta) * sample_cov + delta * target
    return shrunk


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
