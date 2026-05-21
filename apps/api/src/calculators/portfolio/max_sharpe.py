"""Max-Sharpe portfolio.

The raw problem is non-convex:
    maximize  (μ - rf·1)ᵀw / sqrt(wᵀΣw)
    s.t.      1ᵀw = 1, w ≥ 0

But it converts to a convex QP via the standard change of variables
(Cornuejols & Tütüncü). Define y ∈ R^n_≥0 and κ ≥ 0 with
    (μ - rf·1)ᵀy = 1,    κ = 1ᵀy
then minimise  yᵀΣy  s.t.  y ≥ 0,  (μ - rf·1)ᵀy = 1.
Recovered weights:  w = y / κ.

This makes the problem solvable by the same QP solver as mean-variance,
which means we can rely on it being deterministic and convergent.
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

CALCULATOR_ID = "max_sharpe_qp"
METHOD_NAME = "Max-Sharpe (convex reformulation, cvxpy QP)"


def solve(
    req: PortfolioRequest,
    returns_matrix: npt.NDArray[np.float64],
    *,
    solver: str | None = None,
) -> tuple[npt.NDArray[np.float64], dict[str, float | int | str]]:
    mu, cov = returns_stats(returns_matrix)
    excess = mu - req.risk_free_rate
    n = len(mu)

    # Edge case: if no asset has positive excess return, max-Sharpe is
    # undefined (the change-of-variables constraint is infeasible). Fall
    # back to the minimum-variance portfolio.
    if np.max(excess) <= 0:
        w = cp.Variable(n, nonneg=True)
        problem = cp.Problem(
            cp.Minimize(cp.quad_form(w, cov)), [cp.sum(w) == 1.0]
        )
        chosen = solver or cp.CLARABEL
        problem.solve(solver=chosen)
        if w.value is None:
            raise RuntimeError(
                f"Min-variance fallback returned no solution ({problem.status})"
            )
        return np.asarray(w.value, dtype=np.float64), {
            "solver": chosen,
            "status": str(problem.status),
            "iterations": int(problem.solver_stats.num_iters or 0)
            if problem.solver_stats and problem.solver_stats.num_iters is not None
            else 0,
            "fallback": "min_variance_no_positive_excess",
        }

    y = cp.Variable(n, nonneg=True)
    problem = cp.Problem(
        cp.Minimize(cp.quad_form(y, cov)),
        [excess @ y == 1.0],
    )
    chosen = solver or cp.CLARABEL
    problem.solve(solver=chosen)

    if y.value is None:
        raise RuntimeError(
            f"Max-Sharpe solver returned no solution ({problem.status})"
        )

    y_val = np.asarray(y.value, dtype=np.float64)
    kappa = y_val.sum()
    if kappa <= 0:
        raise RuntimeError("Max-Sharpe change-of-variables produced κ ≤ 0")
    weights = y_val / kappa
    return weights, {
        "solver": chosen,
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
        mu, cov = returns_stats(returns_matrix)
        rc = risk_contributions(weights, cov)
        port_ret = portfolio_return(weights, mu)
        port_vol = portfolio_volatility(weights, cov)
        sharpe = (port_ret - req.risk_free_rate) / port_vol if port_vol > 0 else 0.0

        payload = PortfolioPayload(
            objective=PortfolioObjective.MAX_SHARPE,
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
                objective=PortfolioObjective.MAX_SHARPE,
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
