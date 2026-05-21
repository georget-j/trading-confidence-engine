"""Invariant and KKT checks for portfolio optimization.

For a long-only, fully-invested mean-variance portfolio:
    L(w, λ, μ) = -μᵀw + (γ/2)wᵀΣw + λ(1ᵀw - 1) - μᵢwᵢ
KKT conditions at the optimum:
    1. Stationarity:           γΣw - μ + λ·1 - μ_dual = 0
    2. Primal feasibility:     1ᵀw = 1,  w ≥ 0
    3. Dual feasibility:       μ_dual ≥ 0
    4. Complementary slack:    μ_dual_i · w_i = 0

Together with (2) and the optimality of λ (chosen so KKT holds), we can
*derive* the implied dual variables from a candidate weight vector and
check (1), (3), (4). That's what this module does — a sanity check that
the cvxpy solution is actually a KKT point.
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

from src.calculators.portfolio._common import returns_stats
from src.core.schemas import (
    CalculatorResult,
    InvariantCheck,
    PortfolioObjective,
    PortfolioPayload,
    PortfolioRequest,
)

# Mixed tolerance. Convex QP solvers typically converge to ~1e-6 in primal/dual
# residuals; we allow 1e-3 absolute on stationarity to be safe across solvers.
WEIGHT_SUM_TOL = 1e-4
WEIGHT_NEG_TOL = 1e-6
KKT_STATIONARITY_TOL = 1e-3


def check_portfolio_invariants(
    req: PortfolioRequest,
    result: CalculatorResult,
    returns_matrix: npt.NDArray[np.float64],
) -> list[InvariantCheck]:
    checks: list[InvariantCheck] = []
    if not result.succeeded or not isinstance(result.payload, PortfolioPayload):
        checks.append(
            InvariantCheck(
                name="solver_succeeded",
                description="The optimizer produced a result",
                passed=False,
                detail=result.error,
            )
        )
        return checks

    payload = result.payload
    weights = np.array([aw.weight for aw in payload.weights], dtype=np.float64)

    checks.append(_weights_finite(weights))
    checks.append(_weights_non_negative(weights))
    checks.append(_weights_sum_to_one(weights))
    checks.append(_risk_contributions_sum_to_one(payload))
    if payload.objective == PortfolioObjective.MEAN_VARIANCE:
        checks.append(_kkt_stationarity(req, weights, returns_matrix))
    return checks


def _weights_finite(weights: npt.NDArray[np.float64]) -> InvariantCheck:
    passed = bool(np.all(np.isfinite(weights)))
    return InvariantCheck(
        name="weights_finite",
        description="All portfolio weights are finite numbers",
        passed=passed,
        detail=None if passed else "NaN or infinity in weights",
    )


def _weights_non_negative(weights: npt.NDArray[np.float64]) -> InvariantCheck:
    min_w = float(np.min(weights))
    passed = min_w >= -WEIGHT_NEG_TOL
    return InvariantCheck(
        name="weights_non_negative",
        description="Weights ≥ 0 (long-only constraint)",
        passed=passed,
        detail=None if passed else f"min weight={min_w}",
    )


def _weights_sum_to_one(weights: npt.NDArray[np.float64]) -> InvariantCheck:
    total = float(weights.sum())
    passed = math.isclose(total, 1.0, abs_tol=WEIGHT_SUM_TOL)
    return InvariantCheck(
        name="weights_sum_to_one",
        description="Weights sum to 1 (fully-invested constraint)",
        passed=passed,
        detail=None if passed else f"sum={total}",
    )


def _risk_contributions_sum_to_one(payload: PortfolioPayload) -> InvariantCheck:
    total = sum(aw.risk_contribution for aw in payload.weights)
    # Wider tolerance — risk contributions are a derived quantity and can carry
    # rounding error from a noisy covariance matrix.
    passed = math.isclose(total, 1.0, abs_tol=1e-3)
    return InvariantCheck(
        name="risk_contributions_sum_to_one",
        description="Per-asset risk contributions sum to 1",
        passed=passed,
        detail=None if passed else f"sum={total}",
    )


def _kkt_stationarity(
    req: PortfolioRequest,
    weights: npt.NDArray[np.float64],
    returns_matrix: npt.NDArray[np.float64],
) -> InvariantCheck:
    """Verify the mean-variance optimum satisfies the KKT stationarity condition.

    Lagrangian for max μᵀw − (γ/2)wᵀΣw s.t. 1ᵀw = 1, w ≥ 0:
        L = −μᵀw + (γ/2)wᵀΣw + λ(1ᵀw − 1) − μ_dᵀw       (μ_d ≥ 0)
        ∂L/∂w_i = 0  ⟹  μ_d_i = g_i + λ      where  g_i = γΣw_i − μ_i

    Therefore:
      - ACTIVE   (w_i > 0, μ_d_i = 0):   g_i = −λ. All active g_i must equal
                                          a common value (which equals −λ).
      - INACTIVE (w_i = 0, μ_d_i ≥ 0):   g_i ≥ −λ. Negative deviation is the
                                          violation.

    We estimate −λ as the mean of g on the active set, then check both
    conditions against KKT_STATIONARITY_TOL.
    """
    mu, cov = returns_stats(returns_matrix)
    g = req.risk_aversion * (cov @ weights) - mu

    active = weights > 1e-6
    if not np.any(active):
        return InvariantCheck(
            name="kkt_stationarity",
            description="Mean-variance KKT stationarity holds at the solution",
            passed=False,
            detail="No active weights — degenerate solution",
        )

    g_active = g[active]
    lam_est = float(np.mean(g_active))  # this is −λ
    active_deviation = float(np.max(np.abs(g_active - lam_est)))

    # Inactive constraints: require g_i ≥ −λ. Violation magnitude is how far
    # below −λ the worst inactive g_i sits. Positive values of (lam_est − g_i)
    # indicate violation; we clip at 0.
    inactive_violation = 0.0
    if not np.all(active):
        g_inactive = g[~active]
        inactive_violation = float(max(0.0, np.max(lam_est - g_inactive)))

    passed = (
        active_deviation <= KKT_STATIONARITY_TOL
        and inactive_violation <= KKT_STATIONARITY_TOL
    )
    detail = (
        None
        if passed
        else (
            f"active-set deviation from −λ={lam_est:.6g}: {active_deviation:.3e}; "
            f"inactive-set violation (should be 0): {inactive_violation:.3e}"
        )
    )
    return InvariantCheck(
        name="kkt_stationarity",
        description="Mean-variance KKT stationarity holds at the solution",
        passed=passed,
        detail=detail,
    )
