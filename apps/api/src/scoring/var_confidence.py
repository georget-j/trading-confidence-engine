"""VaR-specific confidence scoring.

Differs from options scoring in the meaning of `method_agreement_score`:

- 1.0  tight agreement (all three methods within 5%)         -> verified
- 0.5  wide but acceptable agreement (within 20%)            -> partially
- 0.0  divergent (any pair beyond 20%)                       -> not verified
"""

from __future__ import annotations

from src.core.schemas import (
    CrossMethodCheck,
    InvariantCheck,
    PerMethodStatus,
    VerificationResult,
    VerificationStatus,
)
from src.verification.cross_method_var import VAR_TIGHT_REL_TOL


def score_var_verification(
    *,
    cross_check: CrossMethodCheck | None,
    invariants: list[InvariantCheck],
    input_quality: float,
    numerical_stability: float,
    per_method_status: list[PerMethodStatus] | None = None,
) -> VerificationResult:
    bounds_score = 1.0 if all(i.passed for i in invariants) else 0.0

    if cross_check is None:
        agreement = 0.0
    elif (
        cross_check.passed
        and cross_check.max_relative_delta <= VAR_TIGHT_REL_TOL
    ):
        agreement = 1.0
    elif cross_check.passed:
        agreement = 0.5  # within wide band but not tight
    else:
        agreement = 0.0

    overall = _decide(agreement, bounds_score, input_quality, cross_check)
    return VerificationResult(
        cross_method=cross_check,
        invariants=invariants,
        per_method_status=per_method_status or [],
        method_agreement_score=agreement,
        bounds_check_score=bounds_score,
        input_quality_score=input_quality,
        numerical_stability_score=numerical_stability,
        overall_status=overall,
    )


def _decide(
    agreement: float,
    bounds: float,
    input_quality: float,
    cross_check: CrossMethodCheck | None,
) -> VerificationStatus:
    if bounds < 1.0:
        return VerificationStatus.NOT_VERIFIED
    if input_quality < 0.5:
        return VerificationStatus.NOT_VERIFIED
    if cross_check is None or agreement == 0.0:
        return VerificationStatus.NOT_VERIFIED
    if agreement >= 1.0 and input_quality >= 0.8:
        return VerificationStatus.VERIFIED
    return VerificationStatus.PARTIALLY_VERIFIED
