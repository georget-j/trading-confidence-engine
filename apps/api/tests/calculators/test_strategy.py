"""Multi-leg options strategy tests.

The strategy machinery reuses the existing single-leg pricers, so these tests
focus on the *composition* properties:

1. net_premium and net_greeks are exact quantity-weighted sums.
2. Cross-method check (leg-level) passes for textbook spreads.
3. Per-leg invariant suite runs and labels legs correctly.
4. Pre-set strategies (vertical, iron condor, calendar) verify cleanly.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.calculators.options import black_scholes
from src.calculators.options.strategy import (
    compute_bsm,
    run_strategy_calculators,
)
from src.core.schemas import (
    OptionsPricingRequest,
    OptionsStrategyPayload,
    OptionsStrategyRequest,
    OptionType,
    StrategyLeg,
)
from src.verification.cross_method_strategy import cross_check_strategy_methods
from src.verification.invariants_strategy import check_strategy_invariants

# ---- Fixtures --------------------------------------------------------------


def _make_vertical(spot: float = 450.0) -> OptionsStrategyRequest:
    """Long call vertical (debit): +1 ATM call, -1 OTM call. Both 30 days."""
    return OptionsStrategyRequest(
        spot=spot,
        risk_free_rate=0.05,
        dividend_yield=0.013,
        legs=[
            StrategyLeg(
                option_type=OptionType.CALL,
                strike=spot,
                quantity=1,
                time_to_expiry_years=30 / 365,
                volatility=0.20,
            ),
            StrategyLeg(
                option_type=OptionType.CALL,
                strike=spot * 1.05,
                quantity=-1,
                time_to_expiry_years=30 / 365,
                volatility=0.20,
            ),
        ],
    )


def _make_iron_condor(spot: float = 450.0) -> OptionsStrategyRequest:
    """Iron condor: short ATM call+put inside, long OTM call+put outside."""
    return OptionsStrategyRequest(
        spot=spot,
        risk_free_rate=0.05,
        dividend_yield=0.013,
        legs=[
            StrategyLeg(  # short put 5% OTM (sell premium)
                option_type=OptionType.PUT,
                strike=spot * 0.95,
                quantity=-1,
                time_to_expiry_years=30 / 365,
                volatility=0.22,
            ),
            StrategyLeg(  # long put 10% OTM (wing)
                option_type=OptionType.PUT,
                strike=spot * 0.90,
                quantity=1,
                time_to_expiry_years=30 / 365,
                volatility=0.22,
            ),
            StrategyLeg(  # short call 5% OTM
                option_type=OptionType.CALL,
                strike=spot * 1.05,
                quantity=-1,
                time_to_expiry_years=30 / 365,
                volatility=0.22,
            ),
            StrategyLeg(  # long call 10% OTM
                option_type=OptionType.CALL,
                strike=spot * 1.10,
                quantity=1,
                time_to_expiry_years=30 / 365,
                volatility=0.22,
            ),
        ],
    )


def _make_calendar(spot: float = 450.0) -> OptionsStrategyRequest:
    """Calendar spread: short near-term ATM call, long far-term ATM call."""
    return OptionsStrategyRequest(
        spot=spot,
        risk_free_rate=0.05,
        dividend_yield=0.013,
        legs=[
            StrategyLeg(
                option_type=OptionType.CALL,
                strike=spot,
                quantity=-1,
                time_to_expiry_years=30 / 365,
                volatility=0.20,
            ),
            StrategyLeg(
                option_type=OptionType.CALL,
                strike=spot,
                quantity=1,
                time_to_expiry_years=90 / 365,
                volatility=0.20,
            ),
        ],
    )


# ---- Composition properties (the math, not the pricers) -------------------


def test_net_premium_equals_weighted_sum_of_leg_prices() -> None:
    req = _make_vertical()
    result = compute_bsm(req)
    assert result.succeeded
    payload = result.payload
    assert isinstance(payload, OptionsStrategyPayload)
    expected = sum(leg.quantity * leg.price for leg in payload.legs)
    assert abs(payload.net_premium - expected) < 1e-9


def test_net_greeks_equal_weighted_sum() -> None:
    req = _make_iron_condor()
    result = compute_bsm(req)
    assert result.succeeded
    payload = result.payload
    assert isinstance(payload, OptionsStrategyPayload)

    for greek in ("delta", "gamma", "vega", "theta", "rho"):
        expected = sum(
            leg.quantity * getattr(leg.greeks, greek)
            for leg in payload.legs
            if leg.greeks is not None
        )
        actual = getattr(payload.net_greeks, greek)
        assert abs(actual - expected) < 1e-9, f"net_{greek} mismatch"


def test_long_vertical_matches_single_leg_difference() -> None:
    """+1 ATM call - 1 OTM call should net to BSM(ATM) - BSM(OTM) exactly."""
    spot = 450.0
    req = _make_vertical(spot)
    strategy = compute_bsm(req)
    assert strategy.succeeded

    atm_only = black_scholes.compute(
        OptionsPricingRequest(
            spot=spot,
            strike=spot,
            time_to_expiry_years=30 / 365,
            volatility=0.20,
            risk_free_rate=0.05,
            dividend_yield=0.013,
            option_type=OptionType.CALL,
        )
    )
    otm_only = black_scholes.compute(
        OptionsPricingRequest(
            spot=spot,
            strike=spot * 1.05,
            time_to_expiry_years=30 / 365,
            volatility=0.20,
            risk_free_rate=0.05,
            dividend_yield=0.013,
            option_type=OptionType.CALL,
        )
    )
    assert atm_only.succeeded and otm_only.succeeded
    expected_net = atm_only.payload.price - otm_only.payload.price  # type: ignore[union-attr]

    payload = strategy.payload
    assert isinstance(payload, OptionsStrategyPayload)
    assert abs(payload.net_premium - expected_net) < 1e-9


# ---- Cross-method verification --------------------------------------------


def test_cross_check_passes_for_textbook_vertical() -> None:
    req = _make_vertical()
    results = run_strategy_calculators(req)
    cross = cross_check_strategy_methods(results)
    assert cross is not None
    assert cross.passed, (
        f"vertical: max_abs={cross.max_absolute_delta:g}, "
        f"max_rel={cross.max_relative_delta:g}"
    )


def test_cross_check_passes_for_iron_condor() -> None:
    req = _make_iron_condor()
    results = run_strategy_calculators(req)
    cross = cross_check_strategy_methods(results)
    assert cross is not None
    assert cross.passed


def test_cross_check_passes_for_calendar_spread() -> None:
    req = _make_calendar()
    results = run_strategy_calculators(req)
    cross = cross_check_strategy_methods(results)
    assert cross is not None
    assert cross.passed


def test_cross_check_reports_worst_leg_disagreement() -> None:
    """The CrossMethodCheck must surface the WORST per-leg disagreement,
    not the net premium delta (otherwise opposite-sign legs hide drift)."""
    req = _make_iron_condor()
    results = run_strategy_calculators(req)
    bsm = next(r for r in results if "bsm" in r.calculator_id)
    binom = next(r for r in results if "binomial" in r.calculator_id)
    bsm_payload = bsm.payload
    binom_payload = binom.payload
    assert isinstance(bsm_payload, OptionsStrategyPayload)
    assert isinstance(binom_payload, OptionsStrategyPayload)

    expected_max_abs = max(
        abs(b.price - q.price)
        for b, q in zip(bsm_payload.legs, binom_payload.legs, strict=True)
    )
    cross = cross_check_strategy_methods(results)
    assert cross is not None
    assert abs(cross.max_absolute_delta - expected_max_abs) < 1e-12


def test_cross_check_returns_none_with_single_method() -> None:
    req = _make_vertical()
    one_method = [compute_bsm(req)]
    cross = cross_check_strategy_methods(one_method)
    assert cross is None


# ---- Invariants -----------------------------------------------------------


def test_per_leg_invariants_run_on_every_leg() -> None:
    req = _make_iron_condor()
    results = run_strategy_calculators(req)
    invariants = check_strategy_invariants(req, results)
    leg_indices = {int(c.name.split("_")[0].lstrip("leg")) for c in invariants}
    assert leg_indices == {0, 1, 2, 3}
    assert all(c.passed for c in invariants), [c for c in invariants if not c.passed]


def test_invariants_handle_no_successful_methods() -> None:
    """If both methods failed, return a single failing 'any_method_succeeded' check."""
    req = _make_vertical()
    from src.core.schemas import CalculatorResult, GreeksPayload

    # Hand-construct two failed results so the union type accepts them.
    fake_payload = OptionsStrategyPayload(
        legs=[],
        net_premium=float("nan"),
        net_greeks=GreeksPayload(delta=0, gamma=0, vega=0, theta=0, rho=0),
    )
    failed = [
        CalculatorResult(
            calculator_id="x",
            method_name="x",
            payload=fake_payload,
            duration_ms=0.0,
            succeeded=False,
            error="forced fail",
        ),
        CalculatorResult(
            calculator_id="y",
            method_name="y",
            payload=fake_payload,
            duration_ms=0.0,
            succeeded=False,
            error="forced fail",
        ),
    ]
    invariants = check_strategy_invariants(req, failed)
    assert len(invariants) == 1
    assert invariants[0].name == "any_method_succeeded"
    assert not invariants[0].passed


# ---- Schema validation ----------------------------------------------------


def test_strategy_requires_at_least_two_legs() -> None:
    with pytest.raises(ValidationError):  # pydantic ValidationError
        OptionsStrategyRequest(
            spot=100,
            risk_free_rate=0.05,
            legs=[
                StrategyLeg(
                    option_type=OptionType.CALL,
                    strike=100,
                    quantity=1,
                    time_to_expiry_years=0.1,
                    volatility=0.2,
                )
            ],
        )


def test_zero_quantity_leg_rejected() -> None:
    with pytest.raises(ValidationError):
        StrategyLeg(
            option_type=OptionType.CALL,
            strike=100,
            quantity=0,
            time_to_expiry_years=0.1,
            volatility=0.2,
        )
