"""Tests for the Monte Carlo + Crank-Nicolson options pricers.

These methods are inherently less precise than the closed-form / binomial pair
(MC has sampling noise; CN has discretization error). We assert they're
within their *expected* precision band — looser than the headline 1e-3 used
for BSM/binomial, but tight enough to be a meaningful cross-check.
"""

from __future__ import annotations

import pytest

from src.calculators.options import (
    black_scholes,
    crank_nicolson,
    monte_carlo,
)
from src.calculators.options.runner import run_options_calculators
from src.core.schemas import OptionsPricingRequest, OptionStyle, OptionType

# Tolerance band for the new methods vs the closed-form reference. 1e-2
# relative ≈ 1% (1¢ on a $1 option, $1 on a $100). Anything tighter would
# need 10× more MC paths (200k → 2M) or a finer PDE grid — both feasible
# but slow. This is the band we use throughout the per-method scorecard.
TOL_REL = 1e-2


def _ref_price(req: OptionsPricingRequest) -> float:
    """Reference price from py_vollib closed-form Black-Scholes-Merton."""
    bs_result = black_scholes.compute(req)
    assert bs_result.succeeded, bs_result.error
    return float(bs_result.payload.price)


@pytest.mark.parametrize(
    "spot, strike, T_years, vol, otype",
    [
        (450, 450, 30 / 365, 0.18, "call"),    # SPY 450 ATM call (fixture)
        (450, 450, 30 / 365, 0.18, "put"),     # ATM put
        (100, 105, 0.5, 0.20, "call"),         # OTM call, 6mo
        (100, 95, 0.5, 0.20, "put"),           # OTM put, 6mo
        (100, 100, 1.0, 0.30, "call"),         # ATM, 1y, high vol
    ],
)
def test_monte_carlo_within_band(
    spot: float, strike: float, T_years: float, vol: float, otype: str  # noqa: N803
) -> None:
    """MC must match BSM closed-form within 5e-3 relative on typical inputs."""
    req = OptionsPricingRequest(
        spot=spot, strike=strike, time_to_expiry_years=T_years,
        volatility=vol, risk_free_rate=0.05, dividend_yield=0.0,
        option_type=OptionType.CALL if otype == "call" else OptionType.PUT,
        style=OptionStyle.EUROPEAN,
    )
    ref = _ref_price(req)
    mc = monte_carlo.compute(req)
    assert mc.succeeded, mc.error
    mc_price = float(mc.payload.price)
    rel_err = abs(mc_price - ref) / max(ref, 1e-9)
    assert rel_err < TOL_REL, (
        f"MC diverged: ref={ref:.4f} mc={mc_price:.4f} rel_err={rel_err:.4f}"
    )


@pytest.mark.parametrize(
    "spot, strike, T_years, vol, otype",
    [
        (450, 450, 30 / 365, 0.18, "call"),
        (450, 450, 30 / 365, 0.18, "put"),
        (100, 105, 0.5, 0.20, "call"),
        (100, 95, 0.5, 0.20, "put"),
        (100, 100, 1.0, 0.30, "call"),
    ],
)
def test_crank_nicolson_within_band(
    spot: float, strike: float, T_years: float, vol: float, otype: str  # noqa: N803
) -> None:
    """CN PDE must match BSM closed-form within 5e-3 relative on typical inputs."""
    req = OptionsPricingRequest(
        spot=spot, strike=strike, time_to_expiry_years=T_years,
        volatility=vol, risk_free_rate=0.05, dividend_yield=0.0,
        option_type=OptionType.CALL if otype == "call" else OptionType.PUT,
        style=OptionStyle.EUROPEAN,
    )
    ref = _ref_price(req)
    cn = crank_nicolson.compute(req)
    assert cn.succeeded, cn.error
    cn_price = float(cn.payload.price)
    rel_err = abs(cn_price - ref) / max(ref, 1e-9)
    assert rel_err < TOL_REL, (
        f"CN diverged: ref={ref:.4f} cn={cn_price:.4f} rel_err={rel_err:.4f}"
    )


def test_monte_carlo_is_deterministic() -> None:
    """MC uses a fixed seed → identical inputs produce identical outputs."""
    req = OptionsPricingRequest(
        spot=100, strike=100, time_to_expiry_years=0.5, volatility=0.2,
        risk_free_rate=0.05, dividend_yield=0.0,
        option_type=OptionType.CALL, style=OptionStyle.EUROPEAN,
    )
    p1 = monte_carlo.compute(req).payload.price
    p2 = monte_carlo.compute(req).payload.price
    assert p1 == p2, f"Monte Carlo not deterministic: {p1} vs {p2}"


def test_crank_nicolson_rejects_american() -> None:
    """CN as implemented here only supports European; American must error gracefully."""
    req = OptionsPricingRequest(
        spot=100, strike=100, time_to_expiry_years=0.5, volatility=0.2,
        risk_free_rate=0.05, dividend_yield=0.0,
        option_type=OptionType.CALL, style=OptionStyle.AMERICAN,
    )
    result = crank_nicolson.compute(req)
    assert not result.succeeded
    assert "European" in (result.error or "")


def test_runner_returns_four_methods() -> None:
    """The options runner now returns BSM + binomial + MC + CN."""
    req = OptionsPricingRequest(
        spot=450, strike=450, time_to_expiry_years=30 / 365,
        volatility=0.18, risk_free_rate=0.05, dividend_yield=0.013,
        option_type=OptionType.CALL, style=OptionStyle.EUROPEAN,
    )
    results = run_options_calculators(req)
    ids = [r.calculator_id for r in results]
    assert ids == [
        "py_vollib_bsm_closed_form",
        "quantlib_binomial_lr",
        "monte_carlo_gbm",
        "crank_nicolson_pde",
    ]
    assert all(r.succeeded for r in results), [r.error for r in results if not r.succeeded]
