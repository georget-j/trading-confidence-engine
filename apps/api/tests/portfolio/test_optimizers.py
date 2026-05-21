"""Numerical correctness tests for the two portfolio optimizers."""

from __future__ import annotations

import numpy as np
import pytest

from src.calculators.portfolio import max_sharpe, mean_variance
from src.calculators.portfolio._common import returns_stats
from src.core.schemas import (
    PortfolioObjective,
    PortfolioPayload,
    PortfolioRequest,
)


def _synthetic_returns(
    n_assets: int = 4, n_days: int = 504, seed: int = 42
) -> tuple[list[str], np.ndarray]:
    rng = np.random.default_rng(seed)
    base = rng.normal(0.0008, 0.012, (n_days, n_assets))
    market = rng.normal(0.0005, 0.008, n_days).reshape(-1, 1)
    tickers = [f"A{i}" for i in range(n_assets)]
    return tickers, base + market


@pytest.fixture
def synthetic_4_asset() -> tuple[PortfolioRequest, np.ndarray]:
    tickers, returns = _synthetic_returns()
    req = PortfolioRequest(
        tickers=tickers, objective=PortfolioObjective.MEAN_VARIANCE
    )
    return req, returns


def test_mean_variance_weights_sum_to_one(synthetic_4_asset) -> None:
    req, returns = synthetic_4_asset
    weights, diag = mean_variance.solve(req, returns)
    assert abs(weights.sum() - 1.0) < 1e-4
    assert np.all(weights >= -1e-6)
    assert "iterations" in diag


def test_mean_variance_higher_risk_aversion_shrinks_concentration(
    synthetic_4_asset,
) -> None:
    """γ=20 (very risk-averse) should produce a more diversified portfolio than γ=0.5."""
    req, returns = synthetic_4_asset
    cautious = req.model_copy(update={"risk_aversion": 20.0})
    aggressive = req.model_copy(update={"risk_aversion": 0.5})

    w_c, _ = mean_variance.solve(cautious, returns)
    w_a, _ = mean_variance.solve(aggressive, returns)

    # Concentration metric: max single-asset weight.
    assert w_c.max() < w_a.max(), (
        f"More risk-averse portfolio should be less concentrated; "
        f"got max(cautious)={w_c.max():.3f} vs max(aggressive)={w_a.max():.3f}"
    )


def test_max_sharpe_beats_or_equals_mean_variance_sharpe(synthetic_4_asset) -> None:
    """By construction, max-Sharpe should achieve the highest Sharpe ratio
    among all long-only fully-invested portfolios for the same data."""
    _, returns = _synthetic_returns()
    mu, cov = returns_stats(returns)
    rf = 0.04
    base_req = PortfolioRequest(
        tickers=[f"A{i}" for i in range(4)], risk_free_rate=rf
    )

    mv_req = base_req.model_copy(
        update={"objective": PortfolioObjective.MEAN_VARIANCE}
    )
    ms_req = base_req.model_copy(
        update={"objective": PortfolioObjective.MAX_SHARPE}
    )

    w_mv, _ = mean_variance.solve(mv_req, returns)
    w_ms, _ = max_sharpe.solve(ms_req, returns)

    def sharpe(w: np.ndarray) -> float:
        return float((w @ mu - rf) / np.sqrt(w @ cov @ w))

    s_mv, s_ms = sharpe(w_mv), sharpe(w_ms)
    # max-Sharpe is, by construction, at least as good as mean-variance
    # Sharpe over the same feasible set. With the default 40% box constraint
    # active and solver tolerance ~1e-4, the gap can vanish — but max-Sharpe
    # must not lose by more than solver noise.
    assert s_ms >= s_mv - 2e-3, (
        f"max-Sharpe gave a *lower* Sharpe ({s_ms:.4f}) than mean-variance ({s_mv:.4f})"
    )


def test_compute_returns_a_portfoliopayload(synthetic_4_asset) -> None:
    req, returns = synthetic_4_asset
    result = mean_variance.compute(req, returns)
    assert result.succeeded
    assert isinstance(result.payload, PortfolioPayload)
    payload = result.payload
    assert len(payload.weights) == len(req.tickers)
    assert all(aw.ticker == req.tickers[i] for i, aw in enumerate(payload.weights))
    # Risk contributions sum to ~1.
    rc_sum = sum(aw.risk_contribution for aw in payload.weights)
    assert abs(rc_sum - 1.0) < 1e-3


def test_max_sharpe_falls_back_when_no_positive_excess() -> None:
    """If every asset has below-rf return, max-Sharpe falls back to min-vol."""
    rng = np.random.default_rng(7)
    # Returns that average to roughly -1% annualised — far below any plausible rf.
    returns = rng.normal(-0.00004, 0.01, (252, 3))
    req = PortfolioRequest(
        tickers=["A", "B", "C"],
        objective=PortfolioObjective.MAX_SHARPE,
        risk_free_rate=0.05,
    )
    weights, diag = max_sharpe.solve(req, returns)
    assert abs(weights.sum() - 1.0) < 1e-4
    assert np.all(weights >= -1e-6)
    assert diag.get("fallback") == "min_variance_no_positive_excess"
