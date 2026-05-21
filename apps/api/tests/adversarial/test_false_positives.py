"""Adversarial set — broken setups must be rejected, never silently accepted."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.calculators.options.black_scholes import compute as bs_compute
from src.core.schemas import (
    CalculatorResult,
    CrossMethodCheck,
    InvariantCheck,
    OptionsPriceResult,
    OptionsPricingRequest,
    OptionType,
    VerificationStatus,
)
from src.scoring.confidence import score_verification
from src.verification.cross_method import cross_check_methods
from src.verification.invariants import check_options_invariants


def test_negative_spot_rejected_at_schema_layer() -> None:
    """Schema validation catches obvious garbage before any calculator runs."""
    with pytest.raises(ValidationError):
        OptionsPricingRequest(
            spot=-100.0, strike=100.0, time_to_expiry_years=0.5,
            volatility=0.2, risk_free_rate=0.05,
            option_type=OptionType.CALL,
        )


def test_zero_time_to_expiry_rejected_at_schema_layer() -> None:
    with pytest.raises(ValidationError):
        OptionsPricingRequest(
            spot=100.0, strike=100.0, time_to_expiry_years=0.0,
            volatility=0.2, risk_free_rate=0.05,
            option_type=OptionType.CALL,
        )


def test_disagreeing_methods_marked_not_verified() -> None:
    """Inject two fake calculators with disagreeing prices. Pipeline must flag it."""
    req = OptionsPricingRequest(
        spot=100.0, strike=100.0, time_to_expiry_years=0.5,
        volatility=0.2, risk_free_rate=0.05, option_type=OptionType.CALL,
    )
    fake_a = CalculatorResult(
        calculator_id="fake_a", method_name="fake A",
        payload=OptionsPriceResult(price=5.0), duration_ms=0.1, succeeded=True,
    )
    fake_b = CalculatorResult(
        calculator_id="fake_b", method_name="fake B",
        payload=OptionsPriceResult(price=8.0), duration_ms=0.1, succeeded=True,
    )
    check = cross_check_methods([fake_a, fake_b])
    assert check is not None
    assert not check.passed

    invariants = check_options_invariants(req, [fake_a, fake_b])
    verification = score_verification(
        cross_check=check, invariants=invariants,
        input_quality=1.0, numerical_stability=1.0,
    )
    # Disagreement should never produce `verified`. (May still be `not_verified`
    # even if invariants individually pass — disagreement alone is grounds.)
    assert verification.overall_status != VerificationStatus.VERIFIED


def test_invariant_violation_marked_not_verified() -> None:
    """Even with one method, an invariant violation must hard-fail to not_verified."""
    # A "result" that violates the non-negative-price invariant.
    bad_invariant = [
        InvariantCheck(
            name="non_negative_price",
            description="violated by adversarial fixture",
            passed=False,
            detail="forced",
        )
    ]
    fake = CalculatorResult(
        calculator_id="fake", method_name="fake",
        payload=OptionsPriceResult(price=-1.0), duration_ms=0.1, succeeded=True,
    )
    cross = CrossMethodCheck(
        methods_compared=["fake", "fake"], max_absolute_delta=0.0,
        max_relative_delta=0.0, tolerance=1e-3, passed=True,
    )
    verification = score_verification(
        cross_check=cross, invariants=bad_invariant,
        input_quality=1.0, numerical_stability=1.0,
    )
    assert verification.overall_status == VerificationStatus.NOT_VERIFIED
    _ = fake  # held to clarify intent


def test_single_method_degrades_to_partially_verified() -> None:
    """Cross-check requires >=2 methods; one alone is at best `partially_verified`."""
    req = OptionsPricingRequest(
        spot=100.0, strike=100.0, time_to_expiry_years=0.5,
        volatility=0.2, risk_free_rate=0.05, option_type=OptionType.CALL,
    )
    only = bs_compute(req)
    assert only.succeeded
    invariants = check_options_invariants(req, [only])
    cross = cross_check_methods([only])  # None when <2 succeeded
    assert cross is None
    verification = score_verification(
        cross_check=cross, invariants=invariants,
        input_quality=1.0, numerical_stability=1.0,
    )
    assert verification.overall_status == VerificationStatus.PARTIALLY_VERIFIED
