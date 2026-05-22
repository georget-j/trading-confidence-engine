"""Equal-risk-contribution (risk parity) portfolio optimisation.

Spinu (2013) / Maillard, Roncalli, Teïletche (2010) formulation:

    minimize   ½ xᵀΣx − Σ_i log(x_i)
    s.t.       x > 0

The solution x* is unique and homogeneous of degree 1 (any positive scaling
of x* is also optimal). Normalising w = x* / Σ x* gives the portfolio weights.

At the unconstrained optimum, every asset contributes equally to portfolio
variance: w_i · (Σw)_i = constant. That's the "risk parity" property.

Box constraints (max_weight, min_weight) are applied as linear constraints
on x via the relation w_i = x_i / sum(x):

    x_i ≤ max_weight · sum(x)
    x_i ≥ min_weight · sum(x)

Both are linear in x. The objective stays convex. CLARABEL handles the log
term natively; SCS handles it through its exponential cone. ECOS does not
support the log term reliably here, so we don't offer it as the primary.
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

CALCULATOR_ID = "risk_parity_erc"
METHOD_NAME = "Equal-risk-contribution (Spinu/cvxpy log-barrier)"


def solve(
    req: PortfolioRequest,
    returns_matrix: npt.NDArray[np.float64],
    *,
    solver: str | None = None,
) -> tuple[npt.NDArray[np.float64], dict[str, float | int | str]]:
    """Pure-numerical solver. Returns (weights, diagnostics)."""
    _, cov = returns_stats(returns_matrix, shrink_covariance=req.shrink_covariance)
    n = cov.shape[0]

    # x is strictly positive; w = x / sum(x). The log term in the objective
    # already enforces x_i > 0 (the optimum can't be at the boundary).
    x = cp.Variable(n, pos=True)
    sum_x = cp.sum(x)
    objective = cp.Minimize(0.5 * cp.quad_form(x, cov) - cp.sum(cp.log(x)))

    constraints = []
    if req.max_weight < 1.0:
        constraints.append(x <= req.max_weight * sum_x)
    if req.min_weight > 0.0:
        constraints.append(x >= req.min_weight * sum_x)

    problem = cp.Problem(objective, constraints)
    chosen_solver = solver or cp.CLARABEL
    problem.solve(solver=chosen_solver)

    if x.value is None:
        raise RuntimeError(
            f"Risk-parity solver returned no solution (status={problem.status})"
        )

    x_val = np.asarray(x.value, dtype=np.float64)
    weights = x_val / x_val.sum()
    return weights, {
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
            objective=PortfolioObjective.RISK_PARITY,
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
                objective=PortfolioObjective.RISK_PARITY,
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
