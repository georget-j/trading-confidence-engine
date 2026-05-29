"""Portfolio-optimization pipeline.

Stages match the options/VaR pipelines:
    request -> parse -> resolve-data -> calculate -> verify -> explain -> respond

V6-specific: the verification stage runs THREE checks rather than the V1
cross-method comparison:
  1. Invariants (sum=1, KKT, finite, etc.)
  2. Cross-solver agreement (CLARABEL vs SCS — should match for a convex
     problem)
  3. Sensitivity (perturb μ ±1%, observe weight movement)
"""

from __future__ import annotations

import numpy as np

from src.calculators.portfolio import optimize
from src.core.audit import new_audit_log, record
from src.core.schemas import (
    AgreementStatus,
    AuditLog,
    CalcFamily,
    CalculationRequest,
    CalculatorResult,
    CrossMethodCheck,
    FinalAnswer,
    InvariantCheck,
    PerMethodStatus,
    PortfolioPayload,
    PortfolioRequest,
)
from src.data_providers import MarketDataProvider, default_provider
from src.data_providers.market_data import MarketDataError
from src.scoring.portfolio_confidence import (
    STABLE_THRESHOLD,
    score_portfolio_verification,
)
from src.verification.cross_solver_portfolio import cross_check_solvers
from src.verification.invariants_portfolio import check_portfolio_invariants
from src.verification.sensitivity_portfolio import compute_instability


def run_portfolio_pipeline(
    request: CalculationRequest,
    portfolio_request: PortfolioRequest,
    *,
    provider: MarketDataProvider | None = None,
) -> tuple[FinalAnswer, AuditLog]:
    log = new_audit_log(request.request_id)
    record(log, "request", request.model_dump(mode="json"))
    record(log, "parse", portfolio_request.model_dump(mode="json"))

    # ---- resolve data ----------------------------------------------------
    prov = provider or default_provider()
    try:
        tickers, returns_nested = prov.fetch_aligned_returns(
            portfolio_request.tickers, portfolio_request.lookback_days
        )
    except MarketDataError:
        raise

    returns_matrix = np.asarray(returns_nested, dtype=np.float64)
    if returns_matrix.ndim != 2 or returns_matrix.shape[1] != len(tickers):
        raise MarketDataError(
            f"Provider returned an unexpectedly shaped matrix: {returns_matrix.shape}"
        )

    # ---- calculate (primary, CLARABEL) ----------------------------------
    primary = optimize(portfolio_request, returns_matrix)
    record(log, "calculate", {"results": [primary.model_dump(mode="json")]})

    # ---- verify ----------------------------------------------------------
    invariants = check_portfolio_invariants(portfolio_request, primary, returns_matrix)

    if (
        primary.succeeded
        and isinstance(primary.payload, PortfolioPayload)
        and len(primary.payload.weights) > 0
    ):
        primary_weights = np.array(
            [aw.weight for aw in primary.payload.weights], dtype=np.float64
        )
        cross = cross_check_solvers(portfolio_request, returns_matrix, primary_weights)
        instability_score, _ = compute_instability(
            portfolio_request, returns_matrix, primary_weights
        )
    else:
        cross = None
        instability_score = 1.0  # unable to assess — treat as max instability

    per_method = _build_portfolio_per_method(
        primary=primary,
        invariants=invariants,
        cross_check=cross,
        instability_score=instability_score,
    )
    verification = score_portfolio_verification(
        cross_check=cross,
        invariants=invariants,
        per_method_status=per_method,
        instability_score=instability_score,
        input_quality=1.0,
        numerical_stability=1.0,
    )
    record(log, "verify", verification.model_dump(mode="json"))

    # Backfill the instability_score into the payload so the UI can show it.
    if primary.succeeded and isinstance(primary.payload, PortfolioPayload):
        updated_payload = primary.payload.model_copy(
            update={"instability_score": instability_score}
        )
        primary = primary.model_copy(update={"payload": updated_payload})

    # ---- explain ---------------------------------------------------------
    if not primary.succeeded or not isinstance(primary.payload, PortfolioPayload):
        raise RuntimeError("Portfolio optimization failed — see audit log.")

    explanation = _build_explanation(
        portfolio_request, primary.payload, verification, instability_score
    )
    record(log, "explain", {"text": explanation})

    answer = FinalAnswer(
        request_id=request.request_id,
        family=CalcFamily.PORTFOLIO_OPTIMIZATION,
        verification_status=verification.overall_status,
        primary_result=primary.payload,
        calculator_results=[primary],
        verification=verification,
        explanation=explanation,
        limitations=_limitations_for(verification, instability_score),
    )
    record(log, "respond", answer.model_dump(mode="json"))
    return answer, log


def _build_portfolio_per_method(
    *,
    primary: CalculatorResult,
    invariants: list[InvariantCheck],
    cross_check: CrossMethodCheck | None,
    instability_score: float,
) -> list[PerMethodStatus]:
    """Per-method rows for the portfolio family.

    The primary CalculatorResult is the CLARABEL solver. When the cross-check
    runs, an additional "scs" pseudo-row is synthesised so the scorecard
    surfaces solver-vs-solver agreement the same way options and VaR surface
    method-vs-method agreement. The sensitivity check is reported on the
    primary row (it's a property of the optimum, not of any one solver).
    """
    rows: list[PerMethodStatus] = []
    passed_names = [c.name for c in invariants if c.passed]
    failed_names = [c.name for c in invariants if not c.passed]
    sensitivity_ok = instability_score <= STABLE_THRESHOLD

    if cross_check is None:
        primary_agreement = AgreementStatus.NOT_APPLICABLE
        primary_divergent: list[str] = []
        cross_partner_id: str | None = None
    else:
        primary_agreement = (
            AgreementStatus.AGREES if cross_check.passed else AgreementStatus.DIVERGES
        )
        # methods_compared = ["clarabel", "scs"]; identify the partner that
        # isn't the primary solver id (clarabel by convention here).
        partners = [m for m in cross_check.methods_compared if m != "clarabel"]
        cross_partner_id = partners[0] if partners else None
        primary_divergent = (
            [cross_partner_id]
            if cross_partner_id and not cross_check.passed
            else []
        )

    rows.append(
        PerMethodStatus(
            method_id=primary.calculator_id,
            method_name=primary.method_name,
            ran=primary.succeeded,
            value=(
                primary.payload.sharpe_ratio
                if primary.succeeded and isinstance(primary.payload, PortfolioPayload)
                else None
            ),
            agreement_status=primary_agreement,
            divergent_against=primary_divergent,
            invariants_passed=passed_names if primary.succeeded else [],
            invariants_failed=failed_names if primary.succeeded else [],
            sensitivity_passed=sensitivity_ok if primary.succeeded else None,
            duration_ms=primary.duration_ms,
            error=primary.error,
        )
    )

    if cross_partner_id is not None and cross_check is not None:
        rows.append(
            PerMethodStatus(
                method_id=cross_partner_id,
                method_name="SCS solver (cross-check)",
                ran=True,
                value=None,  # SCS weights aren't exposed as a CalculatorResult
                agreement_status=primary_agreement,
                divergent_against=(
                    [primary.calculator_id] if not cross_check.passed else []
                ),
                invariants_passed=[],
                invariants_failed=[],
                sensitivity_passed=None,
                duration_ms=None,
                error=None,
            )
        )

    return rows


# Re-raise market data errors as-is so the route handler can return 502.
__all__ = ["run_portfolio_pipeline"]


def _build_explanation(
    req: PortfolioRequest,
    payload: PortfolioPayload,
    verification: object,
    instability: float,
) -> str:
    top = sorted(payload.weights, key=lambda w: -w.weight)[:3]
    top_str = ", ".join(f"{aw.ticker} {aw.weight * 100:.1f}%" for aw in top)
    obj_label = {
        "mean_variance": "mean-variance",
        "max_sharpe": "max-Sharpe",
        "risk_parity": "risk-parity",
    }.get(payload.objective.value, payload.objective.value)
    return (
        f"Optimal {obj_label} portfolio across {len(payload.weights)} assets. "
        f"Top weights: {top_str}. "
        f"Expected return {payload.expected_return_annualised * 100:.2f}% / "
        f"vol {payload.volatility_annualised * 100:.2f}% / "
        f"Sharpe {payload.sharpe_ratio:.2f}. "
        f"Solution stability: {(1.0 - instability) * 100:.0f}%."
    )


def _limitations_for(verification: object, instability: float) -> list[str]:
    out: list[str] = [
        "Expected returns are estimated from past data — they're noisy and "
        "may not predict the future. Sample-mean returns over a few years "
        "have wide confidence intervals.",
        "Covariance estimated from the same window; correlation regimes change.",
    ]
    if instability > 0.25:
        out.append(
            f"Solution moves under small input perturbations (instability "
            f"{instability * 100:.0f}%). Treat the weights as a direction, "
            f"not a precise allocation."
        )
    return out


