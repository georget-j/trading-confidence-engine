"""Numerical agreement and convergence tests for the three VaR methods."""

from __future__ import annotations

import numpy as np
import pytest

from src.calculators.risk import run_var_calculators
from src.calculators.risk.historical import compute as historical_compute
from src.calculators.risk.parametric import compute as parametric_compute
from src.core.schemas import VaRPayload, VaRRequest
from src.verification.cross_method_var import cross_check_var


@pytest.fixture
def normal_returns() -> list[float]:
    rng = np.random.default_rng(42)
    return rng.normal(0.0005, 0.012, 504).tolist()


def test_methods_agree_on_normal_returns(normal_returns: list[float]) -> None:
    """Synthetic normal data: all three methods should agree within tight band."""
    req = VaRRequest(returns=normal_returns, portfolio_value=10_000.0)
    results = run_var_calculators(req, normal_returns)
    assert all(r.succeeded for r in results)

    check = cross_check_var(results)
    assert check is not None
    assert check.passed
    assert check.max_relative_delta < 0.05, (
        f"On normal data the methods should agree to <5%, got "
        f"{check.max_relative_delta:.4f}"
    )


def test_parametric_matches_known_value() -> None:
    """Sanity-anchor parametric against the closed-form VaR formula.

    Compute mu/sigma from the data, then check that parametric returns
    -(mu + sigma * z_alpha) * portfolio_value, where z_alpha = Phi^{-1}(1-conf).
    """
    from scipy import stats

    base = np.array([0.01, -0.01] * 251 + [0.01, -0.01], dtype=np.float64)
    mu = float(base.mean())
    sigma = float(base.std(ddof=1))
    z = float(stats.norm.ppf(1.0 - 0.95))
    expected = -(mu + sigma * z) * 1.0  # portfolio_value = 1.0

    req = VaRRequest(returns=base.tolist(), portfolio_value=1.0, confidence_level=0.95)
    result = parametric_compute(req, base.tolist())
    assert result.succeeded
    payload = result.payload
    assert isinstance(payload, VaRPayload)
    assert abs(payload.var_loss - expected) < 1e-10, (
        f"got {payload.var_loss}, expected {expected}"
    )


def test_monotonic_in_confidence_level(normal_returns: list[float]) -> None:
    """VaR_99 must be at least as large as VaR_95 on the same returns."""
    base = VaRRequest(returns=normal_returns, portfolio_value=10_000.0)
    var_95 = historical_compute(base.model_copy(update={"confidence_level": 0.95}), normal_returns)
    var_99 = historical_compute(base.model_copy(update={"confidence_level": 0.99}), normal_returns)
    assert isinstance(var_95.payload, VaRPayload)
    assert isinstance(var_99.payload, VaRPayload)
    assert var_99.payload.var_loss >= var_95.payload.var_loss


def test_cvar_at_least_var_property(normal_returns: list[float]) -> None:
    """CVaR (Expected Shortfall) must be >= VaR for every method."""
    req = VaRRequest(returns=normal_returns, portfolio_value=10_000.0)
    results = run_var_calculators(req, normal_returns)
    for r in results:
        assert isinstance(r.payload, VaRPayload)
        assert r.payload.cvar_loss >= r.payload.var_loss - 1e-9, r.calculator_id


def test_monte_carlo_is_deterministic(normal_returns: list[float]) -> None:
    """Identical inputs must produce identical Monte Carlo outputs (audit replay)."""
    from src.calculators.risk.monte_carlo import compute as mc_compute

    req = VaRRequest(returns=normal_returns, portfolio_value=10_000.0)
    a = mc_compute(req, normal_returns)
    b = mc_compute(req, normal_returns)
    assert isinstance(a.payload, VaRPayload) and isinstance(b.payload, VaRPayload)
    assert a.payload.var_loss == b.payload.var_loss
    assert a.payload.cvar_loss == b.payload.cvar_loss


def test_horizon_scaling_increases_var(normal_returns: list[float]) -> None:
    """10-day VaR must be roughly sqrt(10) ≈ 3.16x the 1-day VaR."""
    req_1d = VaRRequest(returns=normal_returns, portfolio_value=10_000.0, horizon_days=1)
    req_10d = req_1d.model_copy(update={"horizon_days": 10})
    r1 = parametric_compute(req_1d, normal_returns)
    r10 = parametric_compute(req_10d, normal_returns)
    assert isinstance(r1.payload, VaRPayload) and isinstance(r10.payload, VaRPayload)
    ratio = r10.payload.var_loss / r1.payload.var_loss
    # mu_h scales linearly so the ratio isn't exactly sqrt(10), but for ~zero
    # mean returns it's very close.
    assert 3.0 < ratio < 3.3, ratio


def test_insufficient_data_fails_gracefully() -> None:
    """Fewer than 30 returns must surface as a calculator failure, not a crash."""
    req = VaRRequest(returns=[0.01] * 20, portfolio_value=10_000.0)
    results = run_var_calculators(req, [0.01] * 20)
    assert all(not r.succeeded for r in results)
    for r in results:
        assert r.error is not None
        assert "30" in r.error  # the threshold message


def test_nan_returns_rejected() -> None:
    """NaN values in returns must fail validation rather than poison the math."""
    bad = [0.01] * 30 + [float("nan")] + [0.01] * 30
    req = VaRRequest(returns=bad, portfolio_value=10_000.0)
    results = run_var_calculators(req, bad)
    assert all(not r.succeeded for r in results)


def test_historical_populates_downside_metrics(normal_returns: list[float]) -> None:
    """Historical method populates Sortino/Calmar/MaxDD; other methods leave null."""
    req = VaRRequest(returns=normal_returns, portfolio_value=10_000.0)
    result = historical_compute(req, normal_returns)
    assert result.succeeded
    payload = result.payload
    assert isinstance(payload, VaRPayload)
    assert payload.sortino_ratio is not None
    assert payload.calmar_ratio is not None
    assert payload.max_drawdown is not None
    # Sanity bounds on synthetic normal returns (slight positive drift).
    assert payload.max_drawdown > 0
    # Max DD on a 504-day random walk with positive drift is generally < 50%.
    assert payload.max_drawdown < 0.5

    # Other methods should not populate these fields.
    parametric = parametric_compute(req, normal_returns)
    assert parametric.succeeded
    pp = parametric.payload
    assert isinstance(pp, VaRPayload)
    assert pp.sortino_ratio is None
    assert pp.calmar_ratio is None
    assert pp.max_drawdown is None


def test_sortino_exceeds_sharpe_on_positive_skew() -> None:
    """For an asymmetric series with large positive outliers, Sortino must
    exceed Sharpe (downside dev < total dev)."""
    rng = np.random.default_rng(7)
    # Base normal returns + a few large positive spikes.
    base = rng.normal(0.0008, 0.012, 504)
    base[::50] += 0.05  # ~10 large positive jumps
    returns = base.tolist()
    req = VaRRequest(returns=returns, portfolio_value=10_000.0)
    result = historical_compute(req, returns)
    payload = result.payload
    assert isinstance(payload, VaRPayload)
    assert payload.sortino_ratio is not None
    # Sharpe-equivalent from the same series (annualised mean / annualised stdev).
    daily_mean = float(np.mean(base))
    daily_std = float(np.std(base, ddof=1))
    sharpe = (daily_mean * 252) / (daily_std * np.sqrt(252))
    assert payload.sortino_ratio > sharpe, (
        f"sortino {payload.sortino_ratio:.3f} should exceed sharpe {sharpe:.3f}"
    )
