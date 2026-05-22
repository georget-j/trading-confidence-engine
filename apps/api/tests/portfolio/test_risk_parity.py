"""Risk-parity (ERC) tests.

The defining property of risk parity: in the unconstrained problem, every
asset's marginal contribution to portfolio variance equals every other's.
With box constraints (max_weight/min_weight), the property holds only on
the interior assets.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.calculators.portfolio import risk_parity
from src.calculators.portfolio._common import returns_stats
from src.core.schemas import (
    CalculationRequest,
    PortfolioObjective,
    PortfolioPayload,
    PortfolioRequest,
)
from src.orchestration.portfolio_pipeline import run_portfolio_pipeline


def _synthetic_returns(
    n_assets: int = 4, n_days: int = 504, seed: int = 42
) -> tuple[list[str], np.ndarray]:
    rng = np.random.default_rng(seed)
    # Mix high- and low-vol assets to make risk parity visibly different from
    # equal weight: scale each column by a different factor.
    base = rng.normal(0.0008, 0.012, (n_days, n_assets))
    vol_scales = np.array([0.5, 1.0, 1.5, 2.0])[:n_assets]
    base = base * vol_scales
    market = rng.normal(0.0005, 0.008, n_days).reshape(-1, 1)
    tickers = [f"A{i}" for i in range(n_assets)]
    return tickers, base + market


@pytest.fixture
def synthetic_4_asset() -> tuple[PortfolioRequest, np.ndarray]:
    tickers, returns = _synthetic_returns()
    # Open up max_weight so risk parity can fully express itself.
    req = PortfolioRequest(
        tickers=tickers,
        objective=PortfolioObjective.RISK_PARITY,
        max_weight=1.0,
    )
    return req, returns


class _StubProvider:
    def __init__(self, tickers: list[str], returns: np.ndarray) -> None:
        self._tickers = tickers
        self._returns = returns

    def fetch_daily_returns(self, ticker: str, lookback_days: int) -> list[float]:
        raise NotImplementedError

    def fetch_aligned_returns(
        self, tickers: list[str], lookback_days: int
    ) -> tuple[list[str], list[list[float]]]:
        return list(self._tickers), self._returns.tolist()


def test_risk_parity_weights_sum_to_one(synthetic_4_asset) -> None:
    req, returns = synthetic_4_asset
    weights, _ = risk_parity.solve(req, returns)
    assert abs(weights.sum() - 1.0) < 1e-4
    assert np.all(weights > 0)  # log-barrier guarantees strict positivity


def test_risk_parity_risk_contributions_are_equal_unconstrained(
    synthetic_4_asset,
) -> None:
    """Defining property: unconstrained ERC gives equal RC for every asset."""
    req, returns = synthetic_4_asset
    weights, _ = risk_parity.solve(req, returns)
    _, cov = returns_stats(returns, shrink_covariance=req.shrink_covariance)
    portfolio_var = float(weights @ cov @ weights)
    rcs = weights * (cov @ weights) / portfolio_var
    spread = float(rcs.max() - rcs.min())
    assert spread < 5e-3, f"RC spread too wide: {spread:g}, rcs={rcs}"


def test_risk_parity_lower_vol_asset_gets_higher_weight(
    synthetic_4_asset,
) -> None:
    """ERC inversely scales weight by volatility: low-vol asset → high weight."""
    req, returns = synthetic_4_asset
    weights, _ = risk_parity.solve(req, returns)
    # Asset 0 has the lowest vol scale (0.5), Asset 3 the highest (2.0).
    # Risk parity should give weights[0] > weights[3].
    assert weights[0] > weights[3], f"got {weights}"


def test_risk_parity_respects_max_weight() -> None:
    tickers, returns = _synthetic_returns()
    req = PortfolioRequest(
        tickers=tickers,
        objective=PortfolioObjective.RISK_PARITY,
        max_weight=0.30,
    )
    weights, _ = risk_parity.solve(req, returns)
    assert np.max(weights) <= 0.30 + 1e-4, f"max weight breached: {weights}"


def test_risk_parity_pipeline_verified() -> None:
    """End-to-end: pipeline should report `verified` for a clean 4-asset basket."""
    tickers, returns = _synthetic_returns()
    req = PortfolioRequest(
        tickers=tickers,
        objective=PortfolioObjective.RISK_PARITY,
        max_weight=1.0,
    )
    provider = _StubProvider(tickers, returns)
    answer, _ = run_portfolio_pipeline(
        CalculationRequest(raw_input=""), req, provider=provider
    )
    assert answer.verification_status.value == "verified", (
        f"got {answer.verification_status.value}, "
        f"invariants={[c.name for c in answer.verification.invariants if not c.passed]}"
    )
    assert isinstance(answer.primary_result, PortfolioPayload)
    assert answer.primary_result.objective == PortfolioObjective.RISK_PARITY


def test_risk_parity_invariant_catches_unequal_rcs() -> None:
    """If we hand-craft a payload with deliberately unequal RCs, the ERC
    invariant should flag it."""
    from src.core.schemas import AssetWeight, CalculatorResult
    from src.verification.invariants_portfolio import check_portfolio_invariants

    tickers, returns = _synthetic_returns()
    req = PortfolioRequest(
        tickers=tickers,
        objective=PortfolioObjective.RISK_PARITY,
        max_weight=1.0,
    )
    # Equal weights, but report wildly unequal risk contributions.
    bad_payload = PortfolioPayload(
        objective=PortfolioObjective.RISK_PARITY,
        weights=[
            AssetWeight(ticker=t, weight=0.25, risk_contribution=rc)
            for t, rc in zip(tickers, [0.05, 0.15, 0.30, 0.50], strict=True)
        ],
        expected_return_annualised=0.05,
        volatility_annualised=0.10,
        sharpe_ratio=0.5,
        solver_name="fake",
        iterations=1,
        instability_score=None,
    )
    fake = CalculatorResult(
        calculator_id="fake",
        method_name="fake",
        payload=bad_payload,
        duration_ms=0.0,
        succeeded=True,
    )
    checks = check_portfolio_invariants(req, fake, returns)
    erc_check = next(c for c in checks if c.name == "erc_equal_risk_contribution")
    assert not erc_check.passed, "ERC invariant should catch 5%/50% RC spread"
