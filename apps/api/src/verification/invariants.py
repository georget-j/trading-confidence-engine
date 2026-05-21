"""Domain-invariant checks for options pricing.

These are mathematical facts that any correct pricer MUST satisfy regardless of
implementation. Violating one of them is a hard verification failure — even if
both calculators agree, an invariant violation means both are wrong.
"""

from __future__ import annotations

import math

from src.core.schemas import (
    CalculatorResult,
    InvariantCheck,
    OptionsPriceResult,
    OptionsPricingRequest,
    OptionType,
)

# Tolerance for invariant numerical checks. Mixed absolute / relative: a check
# passes if the violation is within EITHER tolerance. Pure absolute breaks on
# large prices (e.g. a $224 deep-ITM call); pure relative breaks at the zero
# limit. Both is needed.
# Invariants are mathematical identities, but evaluated with floating-point
# arithmetic at finite precision. py_vollib's closed-form arithmetic carries
# ~1e-2 absolute error per price from accumulated exp() / norm.cdf() rounding,
# and when invariants subtract two similar prices (e.g. put-call parity at near
# moneyness) catastrophic cancellation can roughly double that.
#
# The tolerance below catches real implementation bugs (off by >0.5% relative
# OR >$0.05 absolute) while not flagging numerical noise from a correct
# calculation. A genuinely broken invariant — say, a sign-flipped parity — is
# off by dollars, so this leaves several orders of magnitude of headroom.
# Note: put-call parity scales its reference against the underlying price
# (not the cancellation-prone C - P difference), which prevents that check
# from needing artificially loose tolerances.
INVARIANT_ABS_TOL = 5e-2
INVARIANT_REL_TOL = 5e-3


def _within_tol(violation: float, reference: float) -> bool:
    """True if `violation` (signed or unsigned diff) is within abs OR rel tolerance."""
    return abs(violation) <= INVARIANT_ABS_TOL or (
        reference != 0 and abs(violation) / abs(reference) <= INVARIANT_REL_TOL
    )


def check_options_invariants(
    req: OptionsPricingRequest,
    results: list[CalculatorResult],
) -> list[InvariantCheck]:
    """Run every applicable invariant and return the results."""
    checks: list[InvariantCheck] = []
    primary = next(
        (
            r for r in results
            if r.succeeded and isinstance(r.payload, OptionsPriceResult)
        ),
        None,
    )
    if primary is None:
        checks.append(
            InvariantCheck(
                name="any_method_succeeded",
                description="At least one calculator returned a result",
                passed=False,
                detail="No calculator succeeded",
            )
        )
        return checks

    payload = primary.payload
    assert isinstance(payload, OptionsPriceResult)  # narrowing for mypy
    price = payload.price

    checks.append(_non_negative(price))
    checks.append(_lower_bound(req, price))
    checks.append(_upper_bound(req, price))
    if payload.greeks is not None:
        checks.append(_delta_in_range(req, payload.greeks.delta))
        checks.append(_gamma_non_negative(payload.greeks.gamma))

    return checks


def _non_negative(price: float) -> InvariantCheck:
    # Tiny negative tolerated as numerical noise; pure absolute is fine near zero.
    passed = price >= -INVARIANT_ABS_TOL
    return InvariantCheck(
        name="non_negative_price",
        description="Option price must be non-negative",
        passed=passed,
        detail=None if passed else f"price={price}",
    )


def _lower_bound(req: OptionsPricingRequest, price: float) -> InvariantCheck:
    """No-arbitrage lower bound:
       call >= max(S*e^{-qT} - K*e^{-rT}, 0)
       put  >= max(K*e^{-rT} - S*e^{-qT}, 0)
    """
    s_disc = req.spot * math.exp(-req.dividend_yield * req.time_to_expiry_years)
    k_disc = req.strike * math.exp(-req.risk_free_rate * req.time_to_expiry_years)
    if req.option_type == OptionType.CALL:
        lb = max(s_disc - k_disc, 0.0)
    else:
        lb = max(k_disc - s_disc, 0.0)
    violation = lb - price  # positive => price below the lower bound
    passed = violation <= 0 or _within_tol(violation, lb)
    return InvariantCheck(
        name="no_arbitrage_lower_bound",
        description="Price must satisfy no-arbitrage lower bound",
        passed=passed,
        detail=None if passed else f"price={price} < lower_bound={lb}",
    )


def _upper_bound(req: OptionsPricingRequest, price: float) -> InvariantCheck:
    """No-arbitrage upper bound:
       call <= S*e^{-qT}
       put  <= K*e^{-rT}
    """
    if req.option_type == OptionType.CALL:
        ub = req.spot * math.exp(-req.dividend_yield * req.time_to_expiry_years)
    else:
        ub = req.strike * math.exp(-req.risk_free_rate * req.time_to_expiry_years)
    violation = price - ub  # positive => price above the upper bound
    passed = violation <= 0 or _within_tol(violation, ub)
    return InvariantCheck(
        name="no_arbitrage_upper_bound",
        description="Price must satisfy no-arbitrage upper bound",
        passed=passed,
        detail=None if passed else f"price={price} > upper_bound={ub}",
    )


def _delta_in_range(req: OptionsPricingRequest, delta: float) -> InvariantCheck:
    """Call delta in [0, 1]; put delta in [-1, 0]."""
    if req.option_type == OptionType.CALL:
        passed = -INVARIANT_ABS_TOL <= delta <= 1.0 + INVARIANT_ABS_TOL
        rng = "[0, 1]"
    else:
        passed = -1.0 - INVARIANT_ABS_TOL <= delta <= INVARIANT_ABS_TOL
        rng = "[-1, 0]"
    return InvariantCheck(
        name="delta_in_range",
        description=f"Delta must lie in {rng} for {req.option_type.value}",
        passed=passed,
        detail=None if passed else f"delta={delta}",
    )


def _gamma_non_negative(gamma: float) -> InvariantCheck:
    passed = gamma >= -INVARIANT_ABS_TOL
    return InvariantCheck(
        name="gamma_non_negative",
        description="Gamma must be non-negative for vanilla options",
        passed=passed,
        detail=None if passed else f"gamma={gamma}",
    )


def check_put_call_parity(
    req_call: OptionsPricingRequest,
    req_put: OptionsPricingRequest,
    call_price: float,
    put_price: float,
) -> InvariantCheck:
    """Put-call parity:  C - P = S*e^{-qT} - K*e^{-rT}.

    Called from tests where we price both legs ourselves.
    """
    if (req_call.spot != req_put.spot or req_call.strike != req_put.strike
            or req_call.time_to_expiry_years != req_put.time_to_expiry_years
            or req_call.risk_free_rate != req_put.risk_free_rate
            or req_call.dividend_yield != req_put.dividend_yield):
        return InvariantCheck(
            name="put_call_parity",
            description="Put-call parity",
            passed=False,
            detail="call and put requests differ in non-type parameters",
        )
    s_disc = req_call.spot * math.exp(-req_call.dividend_yield * req_call.time_to_expiry_years)
    k_disc = req_call.strike * math.exp(-req_call.risk_free_rate * req_call.time_to_expiry_years)
    rhs = s_disc - k_disc
    lhs = call_price - put_price
    diff = lhs - rhs
    # Scale the relative tolerance against the underlying price (the natural
    # scale for parity) rather than max(|LHS|, |RHS|) — the latter is prone to
    # catastrophic cancellation when C and P are close, making true 5e-5
    # relative errors look like 5e-3 against the difference.
    reference_scale = max(req_call.spot, req_call.strike, abs(lhs), abs(rhs))
    passed = _within_tol(diff, reference_scale)
    return InvariantCheck(
        name="put_call_parity",
        description="C - P == S*e^{-qT} - K*e^{-rT}",
        passed=passed,
        detail=None if passed else f"|LHS - RHS|={abs(diff):g} (LHS={lhs:g}, RHS={rhs:g})",
    )
