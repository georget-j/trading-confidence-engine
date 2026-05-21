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
    AuditLog,
    CalcFamily,
    CalculationRequest,
    FinalAnswer,
    PortfolioPayload,
    PortfolioRequest,
)
from src.data_providers import MarketDataProvider, default_provider
from src.data_providers.market_data import MarketDataError
from src.scoring.portfolio_confidence import score_portfolio_verification
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

    verification = score_portfolio_verification(
        cross_check=cross,
        invariants=invariants,
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
    obj_label = (
        "mean-variance"
        if payload.objective.value == "mean_variance"
        else "max-Sharpe"
    )
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


