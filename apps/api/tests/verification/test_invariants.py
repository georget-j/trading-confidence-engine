"""Property-based tests: invariants must hold for arbitrary valid inputs."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.calculators.options.black_scholes import compute as bs_compute
from src.core.schemas import OptionsPricingRequest, OptionType
from src.verification.invariants import (
    check_options_invariants,
    check_put_call_parity,
)

_REASONABLE_INPUTS = st.builds(
    OptionsPricingRequest,
    spot=st.floats(min_value=1.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    strike=st.floats(min_value=1.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    time_to_expiry_years=st.floats(min_value=1 / 365, max_value=5.0),
    volatility=st.floats(min_value=0.01, max_value=2.0),
    risk_free_rate=st.floats(min_value=-0.05, max_value=0.25),
    dividend_yield=st.floats(min_value=0.0, max_value=0.10),
    option_type=st.sampled_from([OptionType.CALL, OptionType.PUT]),
)


@settings(
    max_examples=80,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(req=_REASONABLE_INPUTS)
def test_no_invariant_violation_under_random_inputs(req: OptionsPricingRequest) -> None:
    result = bs_compute(req)
    if not result.succeeded:
        # Numerical edge cases (e.g. extreme moneyness * vol combinations that hit
        # py_vollib's domain limits) — they should be reported as failures, not
        # silently produce bogus invariants.
        return
    checks = check_options_invariants(req, [result])
    failed = [c for c in checks if not c.passed]
    assert not failed, f"invariant violations: {failed} for {req}"


@settings(
    max_examples=40,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(
    spot=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    strike=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    t=st.floats(min_value=1 / 12, max_value=3.0),
    vol=st.floats(min_value=0.05, max_value=1.0),
    r=st.floats(min_value=-0.02, max_value=0.15),
    q=st.floats(min_value=0.0, max_value=0.06),
)
def test_put_call_parity_holds(
    spot: float, strike: float, t: float, vol: float, r: float, q: float
) -> None:
    call_req = OptionsPricingRequest(
        spot=spot, strike=strike, time_to_expiry_years=t,
        volatility=vol, risk_free_rate=r, dividend_yield=q,
        option_type=OptionType.CALL,
    )
    put_req = call_req.model_copy(update={"option_type": OptionType.PUT})

    c = bs_compute(call_req)
    p = bs_compute(put_req)
    if not (c.succeeded and p.succeeded):
        return
    check = check_put_call_parity(
        call_req, put_req, c.payload.price, p.payload.price
    )
    assert check.passed, check.detail
