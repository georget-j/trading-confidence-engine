"""Pipeline runner — moves a CalculationRequest through every stage.

V0 contract:
    request -> parse -> calculate (>=1 method) -> verify -> explain -> respond

Each stage:
- consumes the previous stage's typed output
- emits a typed object
- writes an audit entry

V0 uses stub calculators so we can prove the pipeline shape end-to-end before
hooking real numerics in V1.
"""

from __future__ import annotations

from src.core.audit import new_audit_log, record
from src.core.schemas import (
    AuditLog,
    CalcFamily,
    CalculationRequest,
    FinalAnswer,
    OptionsPricingRequest,
    ParsedRequest,
    VerificationStatus,
)
from src.parser.options import parse_options_request
from src.scoring.confidence import score_verification
from src.verification.cross_method import HEADLINE_METHOD_IDS, cross_check_methods
from src.verification.invariants import check_options_invariants


def run_pipeline(
    request: CalculationRequest,
    *,
    parsed_payload: OptionsPricingRequest | None = None,
) -> tuple[FinalAnswer, AuditLog]:
    """Execute the full pipeline.

    In V0 the parser is bypassable via `parsed_payload` so tests can pin inputs
    without depending on NL parsing yet. V2 wires the real chat-driven parser.
    """
    log = new_audit_log(request.request_id)
    record(log, "request", request.model_dump(mode="json"))

    # ---- parse -----------------------------------------------------------
    if parsed_payload is not None:
        parsed = ParsedRequest(
            request_id=request.request_id,
            family=CalcFamily.OPTIONS_PRICING,
            payload=parsed_payload,
        )
    else:
        parsed = parse_options_request(request)
    record(log, "parse", parsed.model_dump(mode="json"))

    # The options pipeline only handles options payloads — narrow once.
    options_payload = parsed.payload
    assert isinstance(options_payload, OptionsPricingRequest), (
        "options pipeline received non-options parsed payload"
    )

    # ---- calculate -------------------------------------------------------
    # Lazy import to avoid loading numerical libs (QuantLib, etc.) when not
    # needed — keeps the import graph honest and tests fast.
    from src.calculators.options import run_options_calculators

    calc_results = run_options_calculators(options_payload)
    record(
        log,
        "calculate",
        {"results": [r.model_dump(mode="json") for r in calc_results]},
    )

    # ---- verify ----------------------------------------------------------
    # Headline cross-check uses only the high-precision pair (BSM closed-form +
    # binomial). Monte Carlo and Crank-Nicolson run and surface in the per-
    # method scorecard but do not gate the verified/partially-verified status —
    # their inherent precision is looser than the 1e-3 tolerance.
    cross = cross_check_methods(calc_results, include_ids=HEADLINE_METHOD_IDS)
    invariants = check_options_invariants(options_payload, calc_results)
    verification = score_verification(
        cross_check=cross,
        invariants=invariants,
        input_quality=1.0,
        numerical_stability=1.0,
    )
    record(log, "verify", verification.model_dump(mode="json"))

    # ---- explain ---------------------------------------------------------
    primary = calc_results[0].payload
    explanation = _build_explanation(options_payload, primary, verification.overall_status)
    record(log, "explain", {"text": explanation})

    # ---- respond ---------------------------------------------------------
    answer = FinalAnswer(
        request_id=request.request_id,
        family=parsed.family,
        verification_status=verification.overall_status,
        primary_result=primary,
        calculator_results=list(calc_results),
        verification=verification,
        explanation=explanation,
        limitations=_limitations_for(verification.overall_status),
    )
    record(log, "respond", answer.model_dump(mode="json"))

    return answer, log


def _build_explanation(
    req: OptionsPricingRequest, result: object, status: VerificationStatus
) -> str:
    # `result` is OptionsPriceResult — duck-typed for explanation only.
    price = getattr(result, "price", None)
    label = {
        VerificationStatus.VERIFIED: "verified by cross-method agreement",
        VerificationStatus.PARTIALLY_VERIFIED: "computed but only partially verified",
        VerificationStatus.NOT_VERIFIED: "computed but NOT verified",
    }[status]
    return (
        f"{req.option_type.value.title()} on underlying at {req.spot:g}, "
        f"strike {req.strike:g}, T={req.time_to_expiry_years:g}y, "
        f"vol={req.volatility:.2%}, r={req.risk_free_rate:.2%}: "
        f"price={price:.4f} ({label})."
    )


def _limitations_for(status: VerificationStatus) -> list[str]:
    if status == VerificationStatus.VERIFIED:
        return ["European-style only; not formally proven in Lean."]
    if status == VerificationStatus.PARTIALLY_VERIFIED:
        return [
            "Only one independent method available — agreement could not be cross-checked.",
        ]
    return [
        "Methods disagreed or invariants failed. Do not rely on this result.",
    ]
