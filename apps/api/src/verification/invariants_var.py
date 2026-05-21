"""VaR invariant checks.

Three identities that any correct VaR/CVaR implementation must satisfy:

1. var_loss >= 0 — VaR is a loss; negative would mean "expected gain at the
   risk threshold", which is nonsensical for the lower tail at α<0.5.
2. cvar_loss >= var_loss — Expected Shortfall is the conditional mean of the
   tail beyond VaR, so it must be at least as bad as VaR.
3. var_loss <= portfolio_value — you cannot lose more than the unlevered
   portfolio (we explicitly don't support leverage in V5).

A separate check (covered in the test suite, not here) is monotonicity in the
confidence level: VaR_99 >= VaR_95 for the same data.
"""

from __future__ import annotations

from src.core.schemas import (
    CalculatorResult,
    InvariantCheck,
    VaRPayload,
    VaRRequest,
)

# Small tolerance to absorb floating-point noise — these are exact identities.
INV_TOL = 1e-6


def check_var_invariants(
    req: VaRRequest, results: list[CalculatorResult]
) -> list[InvariantCheck]:
    checks: list[InvariantCheck] = []
    primary = next(
        (
            r
            for r in results
            if r.succeeded and isinstance(r.payload, VaRPayload)
        ),
        None,
    )
    if primary is None:
        return [
            InvariantCheck(
                name="any_method_succeeded",
                description="At least one VaR method returned a result",
                passed=False,
                detail="No calculator succeeded",
            )
        ]

    payload = primary.payload
    assert isinstance(payload, VaRPayload)

    checks.append(_var_non_negative(payload.var_loss))
    checks.append(_cvar_at_least_var(payload.var_loss, payload.cvar_loss))
    checks.append(_var_bounded_by_portfolio(payload.var_loss, req.portfolio_value))
    return checks


def _var_non_negative(var_loss: float) -> InvariantCheck:
    passed = var_loss >= -INV_TOL
    return InvariantCheck(
        name="var_non_negative",
        description="VaR loss must be non-negative",
        passed=passed,
        detail=None if passed else f"var_loss={var_loss}",
    )


def _cvar_at_least_var(var_loss: float, cvar_loss: float) -> InvariantCheck:
    passed = cvar_loss >= var_loss - INV_TOL
    return InvariantCheck(
        name="cvar_at_least_var",
        description="CVaR (Expected Shortfall) must be >= VaR",
        passed=passed,
        detail=None
        if passed
        else f"cvar_loss={cvar_loss} < var_loss={var_loss}",
    )


def _var_bounded_by_portfolio(var_loss: float, portfolio_value: float) -> InvariantCheck:
    passed = var_loss <= portfolio_value + INV_TOL
    return InvariantCheck(
        name="var_bounded_by_portfolio",
        description="Unlevered VaR cannot exceed the portfolio value",
        passed=passed,
        detail=None
        if passed
        else f"var_loss={var_loss} > portfolio_value={portfolio_value}",
    )
