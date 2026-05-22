"""Cross-method verifier for multi-leg options strategies.

The plan calls for **leg-level required, aggregate informational** — so the
headline `CrossMethodCheck.max_absolute_delta` reported here is the WORST
per-leg disagreement between the two methods, not the disagreement on the
net premium. A strategy passes verification iff every leg's two-method prices
agree within tolerance.

Why leg-level: long-call + short-call positions partially cancel in the net
premium, so a $0.10 disagreement on a $5 leg could become an apparent $0.001
disagreement at the aggregate level. The aggregate hides the per-leg drift —
exactly what we don't want.
"""

from __future__ import annotations

from src.core.schemas import (
    CalculatorResult,
    CrossMethodCheck,
    OptionsStrategyPayload,
)
from src.verification.cross_method import (
    DEFAULT_PRICE_ABS_TOL,
    DEFAULT_PRICE_REL_TOL,
)


def cross_check_strategy_methods(
    results: list[CalculatorResult],
    *,
    abs_tol: float = DEFAULT_PRICE_ABS_TOL,
    rel_tol: float = DEFAULT_PRICE_REL_TOL,
) -> CrossMethodCheck | None:
    """Return None if fewer than two successful strategy results are available.

    Reports the WORST per-leg disagreement (absolute and relative). The
    relative scale is the average of the two prices for that leg, matching
    the single-leg cross-method convention.
    """
    payloads: list[tuple[str, OptionsStrategyPayload]] = [
        (r.calculator_id, r.payload)
        for r in results
        if r.succeeded and isinstance(r.payload, OptionsStrategyPayload)
    ]
    if len(payloads) < 2:
        return None

    # All strategy payloads must agree on the leg count + ordering — they
    # come from the same request, so this is invariant by construction.
    n_legs = len(payloads[0][1].legs)
    for cid, p in payloads[1:]:
        if len(p.legs) != n_legs:
            return CrossMethodCheck(
                methods_compared=[cid for cid, _ in payloads],
                max_absolute_delta=float("inf"),
                max_relative_delta=float("inf"),
                tolerance=abs_tol,
                passed=False,
            )

    method_ids = [cid for cid, _ in payloads]
    max_abs = 0.0
    max_rel = 0.0
    for leg_idx in range(n_legs):
        prices = [p.legs[leg_idx].price for _, p in payloads]
        for i in range(len(prices)):
            for j in range(i + 1, len(prices)):
                a, b = prices[i], prices[j]
                abs_d = abs(a - b)
                denom = (abs(a) + abs(b)) / 2.0
                rel_d = abs_d / denom if denom > 0 else 0.0
                max_abs = max(max_abs, abs_d)
                max_rel = max(max_rel, rel_d)

    passed = (max_abs <= abs_tol) or (max_rel <= rel_tol)
    return CrossMethodCheck(
        methods_compared=method_ids,
        max_absolute_delta=max_abs,
        max_relative_delta=max_rel,
        tolerance=abs_tol,
        passed=passed,
    )
