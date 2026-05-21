"""Cross-solver verifier for portfolio optimization.

Convex optimization should give the same answer regardless of solver (modulo
tiny numerical noise). Running CLARABEL + SCS in parallel and checking they
agree is the closest equivalent of V1/V5's cross-method check.

Disagreement here is alarming — it usually means the problem is ill-conditioned
(near-singular covariance) and *both* solvers may be reporting stale
intermediate iterates.
"""

from __future__ import annotations

import cvxpy as cp
import numpy as np
import numpy.typing as npt

from src.calculators.portfolio import max_sharpe, mean_variance
from src.core.schemas import CrossMethodCheck, PortfolioObjective, PortfolioRequest

# Larger than V1's options tolerance because SCS converges to ~1e-4 by default
# (vs CLARABEL's ~1e-8). A genuine disagreement is orders of magnitude bigger.
ABS_TOL = 5e-3
REL_TOL = 5e-3


def cross_check_solvers(
    req: PortfolioRequest,
    returns_matrix: npt.NDArray[np.float64],
    primary_weights: npt.NDArray[np.float64],
) -> CrossMethodCheck | None:
    """Re-solve with SCS and compare to the primary (CLARABEL) weights.

    Returns None if the second solver fails to produce a solution — the
    pipeline interprets None as "single-method only" rather than agreement.
    """
    try:
        if req.objective == PortfolioObjective.MEAN_VARIANCE:
            second_weights, _ = mean_variance.solve(
                req, returns_matrix, solver=cp.SCS
            )
        else:
            second_weights, _ = max_sharpe.solve(
                req, returns_matrix, solver=cp.SCS
            )
    except Exception:  # noqa: BLE001
        return None

    delta = primary_weights - second_weights
    max_abs = float(np.max(np.abs(delta)))
    # Relative delta — use the larger of the two weights for each component.
    denom = np.maximum(np.abs(primary_weights), np.abs(second_weights))
    rel = np.zeros_like(delta)
    mask = denom > 1e-12
    rel[mask] = np.abs(delta[mask]) / denom[mask]
    max_rel = float(np.max(rel))

    passed = max_abs <= ABS_TOL or max_rel <= REL_TOL
    return CrossMethodCheck(
        methods_compared=["clarabel", "scs"],
        max_absolute_delta=max_abs,
        max_relative_delta=max_rel,
        tolerance=ABS_TOL,
        passed=passed,
    )
