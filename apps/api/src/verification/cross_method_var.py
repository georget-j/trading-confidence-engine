"""Cross-method verifier for VaR.

Tolerances are deliberately *looser* than for options. Three reasons:

1. Historical and parametric VaR will genuinely disagree on real returns that
   aren't normal — that disagreement is itself a useful signal, not a bug.
2. Monte Carlo has sampling noise (~1/sqrt(N) at the tail) even at 100k paths.
3. The product goal is to *surface* divergence, not to require all methods to
   agree before reporting anything.

The verifier distinguishes:
- close agreement (all three within tight band)        -> verified
- moderate divergence (worst pair within wider band)   -> partially verified
- large divergence (any pair beyond wide band)         -> not verified
"""

from __future__ import annotations

from src.core.schemas import CalculatorResult, CrossMethodCheck, VaRPayload

# Tight band: VaR methods agree closely (synthetic normal data, etc.)
VAR_TIGHT_REL_TOL = 0.05  # 5% relative agreement -> verified
# Wide band: methods diverge but stay within the same order of magnitude
# (real-world data with mild non-normality).
VAR_WIDE_REL_TOL = 0.20  # 20% relative -> partially verified


def cross_check_var(results: list[CalculatorResult]) -> CrossMethodCheck | None:
    """Returns None if fewer than two methods succeeded."""
    succeeded = [
        r for r in results if r.succeeded and isinstance(r.payload, VaRPayload)
    ]
    if len(succeeded) < 2:
        return None

    values = [r.payload.var_loss for r in succeeded]  # type: ignore[union-attr]
    ids = [r.calculator_id for r in succeeded]

    max_abs = 0.0
    max_rel = 0.0
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            a, b = values[i], values[j]
            d = abs(a - b)
            denom = (abs(a) + abs(b)) / 2.0
            r = d / denom if denom > 0 else 0.0
            max_abs = max(max_abs, d)
            max_rel = max(max_rel, r)

    # `passed` semantics for VaR: True iff max_rel falls within the WIDE band,
    # i.e. the methods at least roughly agree. The scoring layer maps WIDE-band
    # but not TIGHT-band to `partially_verified`, and TIGHT-band to `verified`.
    passed = max_rel <= VAR_WIDE_REL_TOL

    return CrossMethodCheck(
        methods_compared=ids,
        max_absolute_delta=max_abs,
        max_relative_delta=max_rel,
        tolerance=VAR_WIDE_REL_TOL,
        passed=passed,
    )


def is_tight_agreement(check: CrossMethodCheck | None) -> bool:
    """True iff cross-method delta is inside the tight (5%) band."""
    return check is not None and check.passed and check.max_relative_delta <= VAR_TIGHT_REL_TOL
