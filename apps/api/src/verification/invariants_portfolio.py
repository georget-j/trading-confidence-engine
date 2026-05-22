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
    elif payload.objective == PortfolioObjective.RISK_PARITY:
        checks.append(_erc_interior_equal(req, payload, weights))
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


def _erc_interior_equal(
    req: PortfolioRequest,
    payload: PortfolioPayload,
    weights: npt.NDArray[np.float64],
) -> InvariantCheck:
    """Risk-parity invariant: among assets NOT pinned to the max/min weight
    bounds, every asset must contribute (approximately) equally to portfolio
    variance.

    The unconstrained ERC formulation has *exactly* equal risk contributions
    at the optimum. With binding box constraints, only the interior assets
    can attain that — pinned assets get whatever RC their forced weight
    implies. So the check applies to interior assets only.
    """
    rcs = np.array(
        [aw.risk_contribution for aw in payload.weights], dtype=np.float64
    )
    max_w = req.max_weight
    min_w = req.min_weight
    at_lower = weights <= max(min_w, 0.0) + 1e-6
    at_upper = weights >= max_w - 1e-6
    interior = ~at_lower & ~at_upper

    if interior.sum() < 2:
        # 0 or 1 interior weight — equality is trivial.
        return InvariantCheck(
            name="erc_equal_risk_contribution",
            description="Risk contributions equal among unconstrained assets",
            passed=True,
            detail="Fewer than 2 interior weights — trivially satisfied",
        )

    rc_interior = rcs[interior]
    spread = float(rc_interior.max() - rc_interior.min())
    # 2% absolute spread is generous: CLARABEL converges to ~1e-6 on smooth
    # problems, but Ledoit-Wolf shrinkage and finite-precision risk
    # contributions add ~1e-3 of noise.
    passed = spread <= 0.02
    return InvariantCheck(
        name="erc_equal_risk_contribution",
        description="Risk contributions equal among unconstrained assets",
        passed=passed,
        detail=None if passed else f"interior RC spread: {spread:.4f}",
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
    mu, cov = returns_stats(returns_matrix, shrink_covariance=req.shrink_covariance)
    g = req.risk_aversion * (cov @ weights) - mu

    # Classify each weight by which constraint set it sits in. With the
    # max_weight box constraint and possible min_weight floor, KKT now has
    # THREE active sets:
    #   interior:  min < w_i < max  → g_i = −λ  (must agree)
    #   at lower:  w_i ≤ min        → g_i ≥ −λ  (μ_l_i ≥ 0)
    #   at upper:  w_i ≥ max        → g_i ≤ −λ  (μ_u_i ≥ 0)
    max_w = req.max_weight
    min_w = req.min_weight
    at_lower = weights <= max(min_w, 0.0) + 1e-6
    at_upper = weights >= max_w - 1e-6
    interior = ~at_lower & ~at_upper

    if not np.any(interior):
        # Every weight is at a boundary — KKT is structurally satisfied as
        # long as the box constraints are honored. Skip the check.
        return InvariantCheck(
            name="kkt_stationarity",
            description="Mean-variance KKT stationarity holds at the solution",
            passed=True,
            detail="All weights pinned to bounds — check trivially satisfied",
        )

    g_interior = g[interior]
    lam_est = float(np.mean(g_interior))  # this is −λ
    interior_deviation = float(np.max(np.abs(g_interior - lam_est)))

    # Lower-bound (incl. zero floor): g_i ≥ −λ required.
    lower_violation = 0.0
    if np.any(at_lower):
        lower_violation = float(max(0.0, np.max(lam_est - g[at_lower])))

    # Upper-bound active: g_i ≤ −λ required.
    upper_violation = 0.0
    if np.any(at_upper):
        upper_violation = float(max(0.0, np.max(g[at_upper] - lam_est)))

    passed = (
        interior_deviation <= KKT_STATIONARITY_TOL
        and lower_violation <= KKT_STATIONARITY_TOL
        and upper_violation <= KKT_STATIONARITY_TOL
    )
    detail = (
        None
        if passed
        else (
            f"interior deviation from −λ={lam_est:.6g}: {interior_deviation:.3e}; "
            f"lower-bound violation: {lower_violation:.3e}; "
            f"upper-bound violation: {upper_violation:.3e}"
        )
    )
    return InvariantCheck(
        name="kkt_stationarity",
        description="Mean-variance KKT stationarity holds at the solution",
        passed=passed,
        detail=detail,
    )
