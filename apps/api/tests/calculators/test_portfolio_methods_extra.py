"""Tests for the Min-variance + Inverse-volatility portfolio methods."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest

from src.calculators.portfolio import inverse_vol, min_variance
from src.calculators.portfolio.runner import optimize
from src.core.schemas import PortfolioObjective, PortfolioRequest


def _synthetic_returns() -> npt.NDArray[np.float64]:
    """504-day, 4-asset synthetic correlated returns."""
    rng = np.random.default_rng(42)
    return rng.multivariate_normal(
        mean=[0.0006, 0.0008, 0.0003, 0.0001],
        cov=[
            [1.0e-4, 0.5e-4, 0.1e-4, -0.1e-4],
            [0.5e-4, 1.5e-4, 0.0, -0.2e-4],
            [0.1e-4, 0.0, 0.5e-4, 0.0],
            [-0.1e-4, -0.2e-4, 0.0, 0.3e-4],
        ],
        size=504,
    )


def _req(objective: PortfolioObjective, max_weight: float = 1.0) -> PortfolioRequest:
    return PortfolioRequest(
        tickers=["SPY", "QQQ", "GLD", "TLT"],
        lookback_days=504,
        risk_free_rate=0.05,
        objective=objective,
        max_weight=max_weight,
        shrink_covariance=True,
    )


# ---- Minimum-variance -------------------------------------------------------


def test_min_variance_weights_sum_to_one() -> None:
    returns = _synthetic_returns()
    r = min_variance.compute(_req(PortfolioObjective.MIN_VARIANCE), returns)
    assert r.succeeded, r.error
    total = sum(w.weight for w in r.payload.weights)
    assert abs(total - 1.0) < 1e-4, f"weights sum to {total}, expected 1"


def test_min_variance_weights_are_long_only() -> None:
    returns = _synthetic_returns()
    r = min_variance.compute(_req(PortfolioObjective.MIN_VARIANCE), returns)
    assert r.succeeded
    assert all(w.weight >= -1e-6 for w in r.payload.weights)


def test_min_variance_lower_vol_than_equal_weight() -> None:
    """Min-variance must have lower portfolio vol than naive 1/n weights."""
    returns = _synthetic_returns()
    r = min_variance.compute(_req(PortfolioObjective.MIN_VARIANCE), returns)
    assert r.succeeded
    # Naive 1/n vol on the synthetic sample.
    from src.calculators.portfolio._common import portfolio_volatility, returns_stats

    _, cov = returns_stats(returns, shrink_covariance=True)
    n = cov.shape[0]
    eq_weights = np.full(n, 1.0 / n)
    eq_vol = portfolio_volatility(eq_weights, cov)
    assert r.payload.volatility_annualised < eq_vol


# ---- Inverse-volatility -----------------------------------------------------


def test_inverse_vol_weights_sum_to_one() -> None:
    returns = _synthetic_returns()
    r = inverse_vol.compute(_req(PortfolioObjective.INVERSE_VOL), returns)
    assert r.succeeded
    total = sum(w.weight for w in r.payload.weights)
    assert abs(total - 1.0) < 1e-4


def test_inverse_vol_lowest_vol_asset_gets_highest_weight() -> None:
    """The asset with lowest standalone vol gets the largest weight under 1/σ."""
    returns = _synthetic_returns()
    from src.calculators.portfolio._common import returns_stats

    _, cov = returns_stats(returns, shrink_covariance=True)
    vols = np.sqrt(np.diag(cov))
    lowest_vol_idx = int(np.argmin(vols))

    r = inverse_vol.compute(_req(PortfolioObjective.INVERSE_VOL), returns)
    assert r.succeeded
    weights = np.array([w.weight for w in r.payload.weights])
    highest_weight_idx = int(np.argmax(weights))
    assert highest_weight_idx == lowest_vol_idx, (
        f"expected lowest-vol asset idx={lowest_vol_idx} to get highest weight, "
        f"got idx={highest_weight_idx}"
    )


def test_inverse_vol_respects_max_weight() -> None:
    """The clip-and-renormalise pass keeps every weight ≤ max_weight."""
    returns = _synthetic_returns()
    r = inverse_vol.compute(_req(PortfolioObjective.INVERSE_VOL, max_weight=0.3), returns)
    assert r.succeeded
    assert all(w.weight <= 0.3 + 1e-6 for w in r.payload.weights), [
        w.weight for w in r.payload.weights
    ]


# ---- Runner dispatch --------------------------------------------------------


@pytest.mark.parametrize(
    "objective,expected_id",
    [
        (PortfolioObjective.MIN_VARIANCE, "min_variance_qp"),
        (PortfolioObjective.INVERSE_VOL, "inverse_vol"),
    ],
)
def test_runner_dispatches_new_objectives(
    objective: PortfolioObjective, expected_id: str
) -> None:
    returns = _synthetic_returns()
    r = optimize(_req(objective), returns)
    assert r.succeeded
    assert r.calculator_id == expected_id
