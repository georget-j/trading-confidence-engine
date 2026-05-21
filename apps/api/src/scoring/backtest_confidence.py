"""Backtest confidence scoring.

For backtests the verification stack is:
- invariants (finite equity, positions in [0,1])
- walk_forward_reproducible (binary)
- lookahead_clean (binary)
- slippage sensitivity (graded — large PnL collapse on 20bp slippage is a warning)

Scoring:
- verified           : all invariants pass, reproducible, look-ahead clean,
                       slippage_collapse ≤ 0.10
- partially_verified : all invariants pass, reproducible, look-ahead clean,
                       slippage_collapse ≤ 0.50
- not_verified       : invariant failure OR not reproducible OR look-ahead detected
                       OR slippage_collapse > 0.50
"""

from __future__ import annotations

from src.core.schemas import (
    InvariantCheck,
    VerificationResult,
    VerificationStatus,
)


def score_backtest_verification(
    *,
    invariants: list[InvariantCheck],
    walk_forward_reproducible: bool,
    lookahead_clean: bool,
    slippage_collapse: float,
    input_quality: float,
) -> VerificationResult:
    bounds_score = 1.0 if all(i.passed for i in invariants) else 0.0
    stability_score = (
        1.0 - min(slippage_collapse, 1.0)
        if walk_forward_reproducible and lookahead_clean
        else 0.0
    )
    overall = _decide(
        bounds_score,
        walk_forward_reproducible,
        lookahead_clean,
        slippage_collapse,
        input_quality,
    )

    return VerificationResult(
        cross_method=None,  # backtests don't have a cross-method comparator
        invariants=invariants,
        method_agreement_score=1.0 if walk_forward_reproducible else 0.0,
        bounds_check_score=bounds_score,
        input_quality_score=input_quality,
        numerical_stability_score=stability_score,
        overall_status=overall,
    )


def _decide(
    bounds: float,
    reproducible: bool,
    no_lookahead: bool,
    slippage_collapse: float,
    input_quality: float,
) -> VerificationStatus:
    if bounds < 1.0 or not reproducible or not no_lookahead:
        return VerificationStatus.NOT_VERIFIED
    if slippage_collapse > 0.50:
        return VerificationStatus.NOT_VERIFIED
    if slippage_collapse > 0.10 or input_quality < 0.8:
        return VerificationStatus.PARTIALLY_VERIFIED
    return VerificationStatus.VERIFIED
