"""Minimum-variance portfolio optimization.

Objective (the γ → ∞ limit of mean-variance):
    minimize  ½ wᵀΣw
    s.t.      1ᵀw = 1
              w ≥ 0     (long-only, fully invested)
              w_i ≤ max_weight (if set)

This is the canonical "no-return-forecast-required" allocation. Useful when
expected returns are too noisy to trust — variance is generally easier to
estimate than mean. Often the baseline that more sophisticated objectives
need to beat.

Convex QP; cvxpy hands it to CLARABEL by default.
"""

from __future__ import annotations

import time

import cvxpy as cp
import numpy as np
import numpy.typing as npt

from src.calculators.portfolio._common import (
    portfolio_return,
    portfolio_volatility,
    returns_stats,
    risk_contributions,
)
from src.core.schemas import (
    AssetWeight,
    CalculatorResult,
    PortfolioObjective,
    PortfolioPayload,
    PortfolioRequest,
)

CALCULATOR_ID = "min_variance_qp"
METHOD_NAME = "Minimum-variance portfolio (cvxpy QP)"


def solve(
    req: PortfolioRequest,
    returns_matrix: npt.NDArray[np.float64],
    *,
    solver: str | None = None,
) -> tuple[npt.NDArray[np.float64], dict[str, float | int | str]]:
    """Pure solver — returns (weights, diagnostics)."""
    _, cov = returns_stats(returns_matrix, shrink_covariance=req.shrink_covariance)
    n = cov.shape[0]

    w = cp.Variable(n, nonneg=True)
    objective = cp.Minimize(0.5 * cp.quad_form(w, cov))
    constraints = [cp.sum(w) == 1.0]
    if req.max_weight < 1.0:
        constraints.append(w <= req.max_weight)
    if req.min_weight > 0.0:
        constraints.append(w >= req.min_weight)
    problem = cp.Problem(objective, constraints)

    chosen_solver = solver or cp.CLARABEL
    problem.solve(solver=chosen_solver)

    if w.value is None:
        raise RuntimeError(
            f"Min-variance solver returned no solution (status={problem.status})"
        )

    return np.asarray(w.value, dtype=np.float64), {
        "solver": chosen_solver,
        "status": str(problem.status),
        "iterations": int(problem.solver_stats.num_iters or 0)
        if problem.solver_stats and problem.solver_stats.num_iters is not None
        else 0,
    }


def compute(
    req: PortfolioRequest,
    returns_matrix: npt.NDArray[np.float64],
    *,
    solver: str | None = None,
) -> CalculatorResult:
    started = time.perf_counter()
    try:
        weights, diag = solve(req, returns_matrix, solver=solver)
        mu, cov = returns_stats(
            returns_matrix, shrink_covariance=req.shrink_covariance
        )
        rc = risk_contributions(weights, cov)
        port_ret = portfolio_return(weights, mu)
        port_vol = portfolio_volatility(weights, cov)
        sharpe = (port_ret - req.risk_free_rate) / port_vol if port_vol > 0 else 0.0

        payload = PortfolioPayload(
            objective=PortfolioObjective.MIN_VARIANCE,
            weights=[
                AssetWeight(
                    ticker=t,
                    weight=float(weights[i]),
                    risk_contribution=float(rc[i]),
                )
                for i, t in enumerate(req.tickers)
            ],
            expected_return_annualised=port_ret,
            volatility_annualised=port_vol,
            sharpe_ratio=sharpe,
            solver_name=str(diag["solver"]),
            iterations=int(diag["iterations"]) if diag["iterations"] else None,
            instability_score=None,
        )
        return CalculatorResult(
            calculator_id=CALCULATOR_ID,
            method_name=METHOD_NAME,
            payload=payload,
            duration_ms=(time.perf_counter() - started) * 1000.0,
            succeeded=True,
        )
    except Exception as exc:  # noqa: BLE001
        return CalculatorResult(
            calculator_id=CALCULATOR_ID,
            method_name=METHOD_NAME,
            payload=PortfolioPayload(
                objective=PortfolioObjective.MIN_VARIANCE,
                weights=[],
                expected_return_annualised=float("nan"),
                volatility_annualised=float("nan"),
                sharpe_ratio=float("nan"),
                solver_name="",
                iterations=None,
                instability_score=None,
            ),
            duration_ms=(time.perf_counter() - started) * 1000.0,
            succeeded=False,
            error=f"{type(exc).__name__}: {exc}",
        )
