"""Confidence scoring.

Combines the five sub-scores into an overall VerificationStatus:

- verified            : agreement >= 0.95 AND bounds = 1.0 AND input_quality >= 0.8
- partially_verified  : single method only (no cross-check), but bounds pass
- not_verified        : invariant violation OR methods disagree
"""

from __future__ import annotations

from src.core.schemas import (
    CrossMethodCheck,
    InvariantCheck,
    VerificationResult,
    VerificationStatus,
)

VERIFIED_AGREEMENT_THRESHOLD = 0.95
VERIFIED_INPUT_QUALITY_THRESHOLD = 0.8


def score_verification(
    *,
    cross_check: CrossMethodCheck | None,
    invariants: list[InvariantCheck],
    input_quality: float,
    numerical_stability: float,
) -> VerificationResult:
    bounds_score = 1.0 if all(i.passed for i in invariants) else 0.0

    if cross_check is None:
        # Only one calculator succeeded — partial verification at best.
        agreement_score = 0.0
    else:
        agreement_score = 1.0 if cross_check.passed else 0.0

    overall = _decide_status(
        agreement_score=agreement_score,
        bounds_score=bounds_score,
        input_quality=input_quality,
        cross_check=cross_check,
    )

    return VerificationResult(
        cross_method=cross_check,
        invariants=invariants,
        method_agreement_score=agreement_score,
        bounds_check_score=bounds_score,
        input_quality_score=input_quality,
        numerical_stability_score=numerical_stability,
        overall_status=overall,
    )


def _decide_status(
    *,
    agreement_score: float,
    bounds_score: float,
    input_quality: float,
    cross_check: CrossMethodCheck | None,
) -> VerificationStatus:
    # Hard fail: any invariant violation.
    if bounds_score < 1.0:
        return VerificationStatus.NOT_VERIFIED

    # No cross-check available — degrade to partial.
    if cross_check is None:
        if input_quality >= VERIFIED_INPUT_QUALITY_THRESHOLD:
            return VerificationStatus.PARTIALLY_VERIFIED
        return VerificationStatus.NOT_VERIFIED

    # Methods disagreed.
    if agreement_score < VERIFIED_AGREEMENT_THRESHOLD:
        return VerificationStatus.NOT_VERIFIED

    # Input quality below bar — partial.
    if input_quality < VERIFIED_INPUT_QUALITY_THRESHOLD:
        return VerificationStatus.PARTIALLY_VERIFIED

    return VerificationStatus.VERIFIED
