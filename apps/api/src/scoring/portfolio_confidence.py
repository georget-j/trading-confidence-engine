"""Portfolio-specific confidence scoring.

Different from options and VaR scoring because:

- Cross-solver agreement is *expected* (convex problem → unique optimum),
  so disagreement is alarming rather than informative.
- Sensitivity (input perturbation → output movement) is the main signal
  about whether a retail user should trust the weights — fragile optima
  on real noisy returns can flip 50% on a 1% change in inputs.

Scoring:
- verified           : invariants pass, solvers agree, instability ≤ 0.25
- partially_verified : invariants pass, solvers agree, instability ≤ 0.6
                         (or solvers disagree only by a basis point)
- not_verified       : invariant failed OR solvers diverged OR instability > 0.6
"""

from __future__ import annotations

from src.core.schemas import (
    CrossMethodCheck,
    InvariantCheck,
    VerificationResult,
    VerificationStatus,
)

STABLE_THRESHOLD = 0.25  # instability ≤ 0.25  → verified
FRAGILE_THRESHOLD = 0.6  # instability > 0.6   → not verified


def score_portfolio_verification(
    *,
    cross_check: CrossMethodCheck | None,
    invariants: list[InvariantCheck],
    instability_score: float,
    input_quality: float,
    numerical_stability: float,
) -> VerificationResult:
    bounds_score = 1.0 if all(i.passed for i in invariants) else 0.0

    if cross_check is None:
        agreement = 0.0
    elif cross_check.passed:
        agreement = 1.0
    else:
        agreement = 0.0

    overall = _decide(
        agreement=agreement,
        bounds=bounds_score,
        instability=instability_score,
        input_quality=input_quality,
        cross_check=cross_check,
    )

    return VerificationResult(
        cross_method=cross_check,
        invariants=invariants,
        method_agreement_score=agreement,
        bounds_check_score=bounds_score,
        input_quality_score=input_quality,
        # Reuse numerical_stability_score for the sensitivity-derived signal —
        # the retail UI surfaces this as "Solution stability".
        numerical_stability_score=max(0.0, 1.0 - instability_score),
        overall_status=overall,
    )


def _decide(
    *,
    agreement: float,
    bounds: float,
    instability: float,
    input_quality: float,
    cross_check: CrossMethodCheck | None,
) -> VerificationStatus:
    if bounds < 1.0:
        return VerificationStatus.NOT_VERIFIED
    if cross_check is None or agreement < 1.0:
        return VerificationStatus.NOT_VERIFIED
    if instability > FRAGILE_THRESHOLD:
        return VerificationStatus.NOT_VERIFIED
    if instability > STABLE_THRESHOLD or input_quality < 0.8:
        return VerificationStatus.PARTIALLY_VERIFIED
    return VerificationStatus.VERIFIED
