"""Domain-invariant checks for multi-leg options strategies.

Approach: apply the existing single-leg invariant suite to every leg of the
strategy, prefixed with the leg index so a user can tell which leg failed.
Strategy-specific invariants (e.g. expected sign of net premium per strategy
type) are deferred — they need strategy classification which V0/M1 doesn't
have.
"""

from __future__ import annotations

from src.core.schemas import (
    CalculatorResult,
    InvariantCheck,
    OptionsPricingRequest,
    OptionsStrategyPayload,
    OptionsStrategyRequest,
)
from src.verification.invariants import check_options_invariants


def check_strategy_invariants(
    req: OptionsStrategyRequest,
    results: list[CalculatorResult],
) -> list[InvariantCheck]:
    """Run per-leg invariants on every leg, return a flat list with prefixed names.

    The primary strategy result (first successful one) supplies the per-leg
    prices. We synthesise a per-leg `OptionsPricingRequest` + per-leg
    `CalculatorResult` and dispatch to the existing single-leg invariant
    suite, then re-name each check with a `leg{i}_` prefix.
    """
    checks: list[InvariantCheck] = []
    primary = next(
        (
            r for r in results
            if r.succeeded and isinstance(r.payload, OptionsStrategyPayload)
        ),
        None,
    )
    if primary is None:
        checks.append(
            InvariantCheck(
                name="any_method_succeeded",
                description="At least one calculator returned a result",
                passed=False,
                detail="No strategy calculator succeeded",
            )
        )
        return checks

    payload = primary.payload
    assert isinstance(payload, OptionsStrategyPayload)

    for idx, (leg_in, leg_out) in enumerate(zip(req.legs, payload.legs, strict=True)):
        # Synthesise a single-leg OptionsPricingRequest for this leg.
        single_req = OptionsPricingRequest(
            spot=req.spot,
            strike=leg_in.strike,
            time_to_expiry_years=leg_in.time_to_expiry_years,
            volatility=leg_in.volatility,
            risk_free_rate=req.risk_free_rate,
            dividend_yield=req.dividend_yield,
            option_type=leg_in.option_type,
            style=req.style,
        )
        # And a single-leg CalculatorResult carrying just this leg's price.
        from src.core.schemas import OptionsPriceResult

        single_result = CalculatorResult(
            calculator_id=f"{primary.calculator_id}_leg{idx}",
            method_name=f"{primary.method_name} [leg {idx}]",
            payload=OptionsPriceResult(price=leg_out.price, greeks=leg_out.greeks),
            duration_ms=0.0,
            succeeded=True,
        )
        per_leg_checks = check_options_invariants(single_req, [single_result])
        for c in per_leg_checks:
            checks.append(
                InvariantCheck(
                    name=f"leg{idx}_{c.name}",
                    description=f"leg {idx}: {c.description}",
                    passed=c.passed,
                    detail=c.detail,
                )
            )

    return checks
