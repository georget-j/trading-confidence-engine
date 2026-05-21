"""Cross-method verifier.

Compares the outputs of N independent calculators and decides whether they
agree closely enough to call the result `verified`. Tolerances are absolute
on the price and relative on the price (we take the looser of the two so a
$0.0001 absolute difference on a $0.01 option doesn't fail the check).
"""

from __future__ import annotations

from src.core.schemas import CalculatorResult, CrossMethodCheck, OptionsPriceResult

# Defaults chosen for European-vanilla options under typical retail conditions.
# Binomial trees at 801 steps converge to BS within ~1e-4 on price for sensible
# inputs. We allow either absolute OR relative within tolerance to pass — useful
# at both ends (penny options and deep ITM).
DEFAULT_PRICE_ABS_TOL = 1e-3
DEFAULT_PRICE_REL_TOL = 1e-3


def cross_check_methods(
    results: list[CalculatorResult],
    *,
    abs_tol: float = DEFAULT_PRICE_ABS_TOL,
    rel_tol: float = DEFAULT_PRICE_REL_TOL,
) -> CrossMethodCheck | None:
    """Return None if fewer than two successful calculators are available."""
    pairs: list[tuple[str, float]] = [
        (r.calculator_id, r.payload.price)
        for r in results
        if r.succeeded and isinstance(r.payload, OptionsPriceResult)
    ]
    if len(pairs) < 2:
        return None

    method_ids = [p[0] for p in pairs]
    prices = [p[1] for p in pairs]

    # Pairwise deltas: max absolute and max relative (relative to mean of pair).
    max_abs = 0.0
    max_rel = 0.0
    for i in range(len(prices)):
        for j in range(i + 1, len(prices)):
            a, b = prices[i], prices[j]
            abs_d = abs(a - b)
            denom = (abs(a) + abs(b)) / 2.0
            rel_d = abs_d / denom if denom > 0 else 0.0
            max_abs = max(max_abs, abs_d)
            max_rel = max(max_rel, rel_d)

    # Pass if EITHER tolerance is satisfied — covers the "tiny price" case where
    # absolute tolerance is meaningful and the "large price" case where relative is.
    passed = (max_abs <= abs_tol) or (max_rel <= rel_tol)

    return CrossMethodCheck(
        methods_compared=method_ids,
        max_absolute_delta=max_abs,
        max_relative_delta=max_rel,
        tolerance=abs_tol,
        passed=passed,
    )
