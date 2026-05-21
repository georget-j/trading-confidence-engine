"""V9 adversarial property tests.

These are property-based tests that go BEYOND the per-family adversarial
suites. They probe invariants that hold across families and edge cases
the existing checks might miss.

Goal: zero known false positives. If any of these flag an inconsistency
we want to know about it before retail users see it.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.calculators.options.black_scholes import compute as bs_compute
from src.calculators.portfolio import mean_variance
from src.calculators.risk import run_var_calculators
from src.core.schemas import (
    OptionsPricingRequest,
    OptionType,
    PortfolioObjective,
    PortfolioRequest,
    VaRPayload,
    VaRRequest,
)

# ---- Options: cross-family invariants -------------------------------------


@settings(
    max_examples=60,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(
    spot=st.floats(min_value=10.0, max_value=1000.0),
    strike=st.floats(min_value=10.0, max_value=1000.0),
    t=st.floats(min_value=1 / 52, max_value=2.0),
    vol=st.floats(min_value=0.05, max_value=1.5),
    r=st.floats(min_value=-0.02, max_value=0.15),
)
def test_option_price_monotonic_in_vol(
    spot: float, strike: float, t: float, vol: float, r: float
) -> None:
    """Black-Scholes is strictly increasing in volatility for both calls and
    puts. If we bump vol by +5%, the price must not decrease."""
    base = OptionsPricingRequest(
        spot=spot, strike=strike, time_to_expiry_years=t,
        volatility=vol, risk_free_rate=r, dividend_yield=0.0,
        option_type=OptionType.CALL,
    )
    bumped = base.model_copy(update={"volatility": min(vol * 1.05, 5.0)})
    base_price = bs_compute(base)
    bumped_price = bs_compute(bumped)
    if not (base_price.succeeded and bumped_price.succeeded):
        return
    # Allow tiny numerical noise either way (the closed-form has ~1e-2 floor).
    assert bumped_price.payload.price >= base_price.payload.price - 1e-2, (
        f"Price decreased under vol bump: {base_price.payload.price} -> "
        f"{bumped_price.payload.price}"
    )


# ---- VaR: monotonicity in confidence + portfolio scaling -----------------


@settings(
    max_examples=40,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(
    seed=st.integers(min_value=0, max_value=10000),
    portfolio_value=st.floats(min_value=1000.0, max_value=1_000_000.0),
)
def test_var_scales_linearly_with_portfolio(seed: int, portfolio_value: float) -> None:
    """VaR is a linear function of portfolio value — doubling the portfolio
    doubles the dollar VaR (within numerical noise)."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.012, 504).tolist()

    base = VaRRequest(
        returns=returns, portfolio_value=portfolio_value, confidence_level=0.95
    )
    doubled = base.model_copy(update={"portfolio_value": portfolio_value * 2})
    base_results = run_var_calculators(base, returns)
    doubled_results = run_var_calculators(doubled, returns)
    for r1, r2 in zip(base_results, doubled_results, strict=True):
        if not (r1.succeeded and r2.succeeded):
            continue
        assert isinstance(r1.payload, VaRPayload)
        assert isinstance(r2.payload, VaRPayload)
        # Ratio should be exactly 2 (linearity), within float tolerance.
        ratio = r2.payload.var_loss / max(r1.payload.var_loss, 1e-9)
        assert abs(ratio - 2.0) < 1e-6, (
            f"{r1.calculator_id}: doubling portfolio gave ratio {ratio}"
        )


@settings(
    max_examples=40,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(
    seed=st.integers(min_value=0, max_value=10000),
    conf_low=st.floats(min_value=0.51, max_value=0.94),
    conf_high=st.floats(min_value=0.95, max_value=0.999),
)
def test_var_strictly_increasing_in_confidence(
    seed: int, conf_low: float, conf_high: float
) -> None:
    """VaR must be monotonically non-decreasing in the confidence level.
    99% VaR ≥ 95% VaR for the same data."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.012, 504).tolist()
    low = VaRRequest(returns=returns, confidence_level=conf_low, portfolio_value=10_000)
    high = VaRRequest(returns=returns, confidence_level=conf_high, portfolio_value=10_000)
    low_results = run_var_calculators(low, returns)
    high_results = run_var_calculators(high, returns)
    for r1, r2 in zip(low_results, high_results, strict=True):
        if not (r1.succeeded and r2.succeeded):
            continue
        assert isinstance(r1.payload, VaRPayload)
        assert isinstance(r2.payload, VaRPayload)
        assert r2.payload.var_loss >= r1.payload.var_loss - 1e-6, (
            f"{r1.calculator_id}: VaR_{conf_high} < VaR_{conf_low}"
        )


# ---- Portfolio: optimum properties ---------------------------------------


@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(
    seed=st.integers(min_value=0, max_value=1000),
    n_assets=st.integers(min_value=3, max_value=8),
)
def test_portfolio_weights_always_in_bounds(seed: int, n_assets: int) -> None:
    """The optimiser MUST produce weights that satisfy the box constraints
    exactly — sum=1, all in [0, max_weight]."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.012, (252, n_assets))
    req = PortfolioRequest(
        tickers=[f"A{i}" for i in range(n_assets)],
        objective=PortfolioObjective.MEAN_VARIANCE,
        max_weight=0.5,
        shrink_covariance=True,
    )
    weights, _ = mean_variance.solve(req, returns)
    assert abs(weights.sum() - 1.0) < 1e-4
    assert (weights >= -1e-6).all()
    assert (weights <= req.max_weight + 1e-4).all()


@settings(
    max_examples=15,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(seed=st.integers(min_value=0, max_value=1000))
def test_higher_risk_aversion_lowers_variance(seed: int) -> None:
    """Across two solves with γ=1 and γ=20 on the same data, the higher-γ
    portfolio must have non-greater variance."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.012, (252, 5))
    req = PortfolioRequest(
        tickers=[f"A{i}" for i in range(5)], shrink_covariance=False,
        max_weight=1.0,
    )
    low = req.model_copy(update={"risk_aversion": 1.0})
    high = req.model_copy(update={"risk_aversion": 20.0})
    w_low, _ = mean_variance.solve(low, returns)
    w_high, _ = mean_variance.solve(high, returns)
    cov = np.cov(returns, rowvar=False, ddof=1)
    var_low = float(w_low @ cov @ w_low)
    var_high = float(w_high @ cov @ w_high)
    assert var_high <= var_low + 1e-6, (
        f"γ=20 gave HIGHER variance ({var_high}) than γ=1 ({var_low})"
    )


# ---- Cross-family: refusing bad inputs is consistent ---------------------


@pytest.mark.parametrize(
    "n_returns",
    [1, 5, 10, 29],
)
def test_var_refuses_insufficient_data(n_returns: int) -> None:
    """All three VaR methods must fail (succeeded=False) on <30 observations.
    None of them should silently return a number."""
    returns = [0.001] * n_returns
    req = VaRRequest(returns=returns, portfolio_value=10_000)
    results = run_var_calculators(req, returns)
    for r in results:
        assert not r.succeeded, (
            f"{r.calculator_id} accepted only {n_returns} returns — should refuse"
        )
        assert r.error is not None
