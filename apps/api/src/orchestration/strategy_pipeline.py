"""Multi-leg options strategy pipeline.

Mirrors the single-leg `pipeline.py` but:
- Calls the per-leg strategy calculator (BSM + binomial under the hood).
- Uses the strategy-specific cross-method verifier (worst per-leg disagreement).
- Uses the strategy-specific invariant suite (per-leg no-arb bounds).

Output is a `FinalAnswer` with `primary_result: OptionsStrategyPayload` and
the per-method `CalculatorResult`s in `calculator_results` so the UI can show
both methods' results side-by-side.
"""

from __future__ import annotations

from src.calculators.options.strategy import run_strategy_calculators
from src.core.audit import new_audit_log, record
from src.core.schemas import (
    AuditLog,
    CalcFamily,
    CalculationRequest,
    CalculatorResult,
    FinalAnswer,
    OptionsStrategyPayload,
    OptionsStrategyRequest,
    ParsedRequest,
    VerificationStatus,
)
from src.scoring.confidence import score_verification
from src.verification.cross_method import (
    DEFAULT_PRICE_ABS_TOL,
    DEFAULT_PRICE_REL_TOL,
)
from src.verification.cross_method_strategy import cross_check_strategy_methods
from src.verification.invariants_strategy import check_strategy_invariants
from src.verification.per_method import build_per_method_status


def run_strategy_pipeline(
    request: CalculationRequest,
    payload: OptionsStrategyRequest,
) -> tuple[FinalAnswer, AuditLog]:
    """Execute the multi-leg pipeline end-to-end."""
    log = new_audit_log(request.request_id)
    record(log, "request", request.model_dump(mode="json"))

    parsed = ParsedRequest(
        request_id=request.request_id,
        family=CalcFamily.OPTIONS_PRICING,
        payload=payload,
    )
    record(log, "parse", parsed.model_dump(mode="json"))

    calc_results = run_strategy_calculators(payload)
    record(
        log,
        "calculate",
        {"results": [r.model_dump(mode="json") for r in calc_results]},
    )

    cross = cross_check_strategy_methods(calc_results)
    invariants = check_strategy_invariants(payload, calc_results)
    per_method = build_per_method_status(
        results=calc_results,
        cross_check=cross,
        value_extractor=_strategy_net_premium_extractor,
        invariant_runner=lambda r: check_strategy_invariants(payload, [r]),
        abs_tol=DEFAULT_PRICE_ABS_TOL,
        rel_tol=DEFAULT_PRICE_REL_TOL,
    )
    verification = score_verification(
        cross_check=cross,
        invariants=invariants,
        per_method_status=per_method,
        input_quality=1.0,
        numerical_stability=1.0,
    )
    record(log, "verify", verification.model_dump(mode="json"))

    primary = calc_results[0].payload
    assert isinstance(primary, OptionsStrategyPayload)
    explanation = _build_explanation(payload, primary, verification.overall_status)
    record(log, "explain", {"text": explanation})

    answer = FinalAnswer(
        request_id=request.request_id,
        family=parsed.family,
        verification_status=verification.overall_status,
        primary_result=primary,
        calculator_results=list(calc_results),
        verification=verification,
        explanation=explanation,
        limitations=_limitations_for(verification.overall_status, len(payload.legs)),
    )
    record(log, "respond", answer.model_dump(mode="json"))

    return answer, log


def _strategy_net_premium_extractor(r: CalculatorResult) -> float | None:
    if r.succeeded and isinstance(r.payload, OptionsStrategyPayload):
        return r.payload.net_premium
    return None


def _build_explanation(
    req: OptionsStrategyRequest,
    result: OptionsStrategyPayload,
    status: VerificationStatus,
) -> str:
    n = len(req.legs)
    net = result.net_premium
    label = {
        VerificationStatus.VERIFIED: "verified by per-leg cross-method agreement",
        VerificationStatus.PARTIALLY_VERIFIED: "computed but only partially verified",
        VerificationStatus.NOT_VERIFIED: "computed but NOT verified",
    }[status]
    side = "debit" if net > 0 else "credit" if net < 0 else "even"
    return (
        f"{n}-leg strategy on underlying at {req.spot:g}, "
        f"net {side} {abs(net):.4f} ({label})."
    )


def _limitations_for(status: VerificationStatus, n_legs: int) -> list[str]:
    base = [
        "European-style only.",
        f"{n_legs} legs priced independently; correlations between legs assumed zero "
        "for verification purposes (each leg's no-arb bound is checked on its own).",
    ]
    if status == VerificationStatus.PARTIALLY_VERIFIED:
        base.append(
            "Cross-method agreement is borderline on at least one leg — "
            "the largest per-leg disagreement is reported above."
        )
    elif status == VerificationStatus.NOT_VERIFIED:
        base.append(
            "Methods disagreed on at least one leg, or a per-leg invariant failed. "
            "Do not rely on this result."
        )
    return base
