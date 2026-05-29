"""VaR pipeline runner.

Same shape as the options pipeline (request -> resolve-data -> calculate ->
verify -> explain -> respond) but specialised for the risk family.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.calculators.risk import run_var_calculators
from src.core.audit import new_audit_log, record
from src.core.schemas import (
    AuditLog,
    CalcFamily,
    CalculationRequest,
    CalculatorResult,
    FinalAnswer,
    VaRPayload,
    VaRRequest,
    VerificationResult,
    VerificationStatus,
)
from src.data_providers import MarketDataProvider, default_provider
from src.data_providers.market_data import MarketDataError
from src.scoring.var_confidence import score_var_verification
from src.verification.cross_method_var import (
    VAR_WIDE_REL_TOL,
    cross_check_var,
)
from src.verification.invariants_var import check_var_invariants
from src.verification.per_method import build_per_method_status


def run_var_pipeline(
    request: CalculationRequest,
    var_request: VaRRequest,
    *,
    provider: MarketDataProvider | None = None,
) -> tuple[FinalAnswer, AuditLog]:
    log = new_audit_log(request.request_id)
    record(log, "request", request.model_dump(mode="json"))
    record(log, "parse", var_request.model_dump(mode="json"))

    # ---- resolve returns -------------------------------------------------
    returns = _resolve_returns(var_request, provider)

    # ---- calculate -------------------------------------------------------
    calc_results = run_var_calculators(var_request, returns)
    record(
        log,
        "calculate",
        {"results": [r.model_dump(mode="json") for r in calc_results]},
    )

    # ---- verify ----------------------------------------------------------
    cross = cross_check_var(calc_results)
    invariants = check_var_invariants(var_request, calc_results)
    per_method = build_per_method_status(
        results=calc_results,
        cross_check=cross,
        value_extractor=_var_loss_extractor,
        invariant_runner=lambda r: check_var_invariants(var_request, [r]),
        # VaR uses pure relative tolerance (the wide band); abs_tol stays 0.
        abs_tol=0.0,
        rel_tol=VAR_WIDE_REL_TOL,
    )
    verification = score_var_verification(
        cross_check=cross,
        invariants=invariants,
        per_method_status=per_method,
        input_quality=1.0 if returns else 0.0,
        numerical_stability=1.0,
    )
    record(log, "verify", verification.model_dump(mode="json"))

    # ---- explain ---------------------------------------------------------
    primary_result = _pick_primary(calc_results)
    if primary_result is None:
        # No calculator succeeded — return a minimal not-verified answer.
        raise MarketDataError("All VaR calculators failed; see audit log.")

    explanation = _build_explanation(
        var_request, primary_result, verification, cross
    )
    record(log, "explain", {"text": explanation})

    answer = FinalAnswer(
        request_id=request.request_id,
        family=CalcFamily.RISK_METRICS,
        verification_status=verification.overall_status,
        primary_result=primary_result,
        calculator_results=list(calc_results),
        verification=verification,
        explanation=explanation,
        limitations=_limitations_for(verification, cross),
    )
    record(log, "respond", answer.model_dump(mode="json"))
    return answer, log


def _var_loss_extractor(r: CalculatorResult) -> float | None:
    if r.succeeded and isinstance(r.payload, VaRPayload):
        return r.payload.var_loss
    return None


def _resolve_returns(
    req: VaRRequest, provider: MarketDataProvider | None
) -> list[float]:
    if req.returns is not None:
        return req.returns
    if req.ticker is None:
        raise MarketDataError(
            "VaRRequest needs either `returns` or `ticker` — both were null."
        )
    prov = provider or default_provider()
    return prov.fetch_daily_returns(req.ticker, req.lookback_days)


def _pick_primary(results: Sequence[CalculatorResult]) -> VaRPayload | None:
    """Use historical as the primary result when available — it makes no
    distributional assumption, so it's the most honest single-number answer."""
    from src.calculators.risk.historical import CALCULATOR_ID as HIST_ID

    historical = next(
        (r for r in results if r.calculator_id == HIST_ID and r.succeeded), None
    )
    if historical and isinstance(historical.payload, VaRPayload):
        return historical.payload
    for r in results:
        if r.succeeded and isinstance(r.payload, VaRPayload):
            return r.payload
    return None


def _build_explanation(
    req: VaRRequest,
    primary: VaRPayload,
    verification: VerificationResult,
    cross: object,
) -> str:
    horizon_label = "day" if req.horizon_days == 1 else f"{req.horizon_days} days"
    return (
        f"{int(req.confidence_level * 100)}% VaR over {horizon_label}: "
        f"${primary.var_loss:,.2f} loss expected to be exceeded with probability "
        f"{(1 - req.confidence_level) * 100:.1f}%. "
        f"Expected shortfall (CVaR): ${primary.cvar_loss:,.2f}. "
        f"Status: {verification.overall_status.value}."
    )


def _limitations_for(
    verification: VerificationResult, cross: object
) -> list[str]:
    out: list[str] = [
        "Methods assume iid returns and use sqrt(T) horizon scaling.",
        "VaR is a statistical estimate, not a guarantee — tail events can exceed it.",
    ]
    if verification.overall_status == VerificationStatus.PARTIALLY_VERIFIED:
        out.append(
            "Historical, parametric, and Monte Carlo VaR diverge moderately — "
            "this usually signals fat tails or non-normal returns. The "
            "parametric (normal) result may be biased; the historical result "
            "is the most distributional-assumption-free."
        )
    if verification.overall_status == VerificationStatus.NOT_VERIFIED:
        out.append(
            "Methods disagree by more than the wide tolerance, or an "
            "invariant failed. Do not rely on this number."
        )
    return out
