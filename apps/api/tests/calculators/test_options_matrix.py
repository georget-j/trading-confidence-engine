"""Cross-method agreement matrix — the V1 acceptance test.

Sweeps a grid of representative options and asserts both calculators agree
within tolerance and produce verified results. Hitting >50 scenarios is a V1
exit criterion.
"""

from __future__ import annotations

import itertools

import pytest

from src.calculators.options import run_options_calculators
from src.core.schemas import (
    CalculationRequest,
    OptionsPricingRequest,
    OptionType,
    VerificationStatus,
)
from src.orchestration.pipeline import run_pipeline
from src.verification.cross_method import cross_check_methods

# A 3 x 3 x 3 x 3 x 2 = 162-scenario grid.
SPOTS = [50.0, 100.0, 250.0]
MONEYNESS = [0.85, 1.00, 1.15]          # K = spot * moneyness
TIMES = [7 / 365, 30 / 365, 1.0]
VOLS = [0.10, 0.25, 0.60]
TYPES = [OptionType.CALL, OptionType.PUT]
R, Q = 0.04, 0.01

_GRID = list(itertools.product(SPOTS, MONEYNESS, TIMES, VOLS, TYPES))


@pytest.mark.parametrize("spot, mny, t, vol, otype", _GRID)
def test_methods_agree_on_grid(
    spot: float, mny: float, t: float, vol: float, otype: OptionType
) -> None:
    req = OptionsPricingRequest(
        spot=spot, strike=spot * mny, time_to_expiry_years=t,
        volatility=vol, risk_free_rate=R, dividend_yield=Q,
        option_type=otype,
    )
    results = run_options_calculators(req)
    assert all(r.succeeded for r in results), [r.error for r in results if not r.succeeded]
    check = cross_check_methods(results)
    assert check is not None
    assert check.passed, (
        f"methods disagreed: abs={check.max_absolute_delta:g} "
        f"rel={check.max_relative_delta:g} for {req}"
    )


def test_full_pipeline_marks_textbook_inputs_as_verified() -> None:
    """End-to-end: standard inputs must end up `verified`."""
    req = OptionsPricingRequest(
        spot=100.0, strike=100.0, time_to_expiry_years=0.5,
        volatility=0.20, risk_free_rate=0.05,
        option_type=OptionType.CALL,
    )
    answer, _ = run_pipeline(CalculationRequest(raw_input=""), parsed_payload=req)
    assert answer.verification_status == VerificationStatus.VERIFIED
