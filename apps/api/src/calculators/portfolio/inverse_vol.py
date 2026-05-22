"""Inverse-volatility weighting.

A pure heuristic — no optimisation. Each asset gets weight proportional to
the inverse of its standalone volatility:

    w_i ∝ 1 / σ_i
    w_i = w_i / Σ_j w_j     (renormalise to sum to 1)

Ignores correlations entirely (unlike min-variance, which uses the full
covariance matrix). The strength of inverse-vol is robustness: it's nearly
impossible to be badly wrong because there's no estimation step beyond
sample variance. The weakness: it underweights low-vol assets even when
they're highly correlated with the rest of the portfolio.

Genuinely independent from the QP-based methods — no solver, no optimisation,
just arithmetic on sample variances. If inverse-vol disagrees with min-variance
or risk-parity, the difference is informative about how much the covariance
structure matters for that universe.

Caveat: ignores the max_weight constraint by design (renormalisation is
proportional, not optimisation). Applied AFTER computing the inverse-vol
weights as a soft clip + renormalise pass.
"""

from __future__ import annotations

import time

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

CALCULATOR_ID = "inverse_vol"
METHOD_NAME = "Inverse-volatility weighting (heuristic, no solver)"


def _apply_max_weight_clip(
    weights: npt.NDArray[np.float64], max_weight: float
) -> npt.NDArray[np.float64]:
    """Iteratively clip + renormalise until every weight is ≤ max_weight.

    Each iteration: clip the over-cap weights to max_weight, redistribute the
    excess across under-cap weights *proportionally*. Loop until no weight
    exceeds the cap, then do a final hard-clip safety pass to guarantee
    `max(w) ≤ max_weight` regardless of iteration count.
    """
    if max_weight >= 1.0:
        return weights
    w = weights.copy()
    TOL = 1e-9  # noqa: N806 — local constant
    for _ in range(2 * len(w)):  # 2N iterations is generous slack
        over = w > max_weight + TOL
        if not np.any(over):
            break
        excess = float((w[over] - max_weight).sum())
        w[over] = max_weight
        under = ~over
        if not np.any(under):
            break
        total_under = float(w[under].sum())
        if total_under <= 0:
            break
        w[under] = w[under] + (excess * w[under] / total_under)

    # Final hard-clip safety pass. After clipping, the sum may dip below 1; the
    # last divide-by-sum renormalises but can't push anything back over max
    # because each w_i < max_weight implies w_i / sum ≤ max_weight when sum ≥
    # (#non-clipped) × min(w_i / max_weight).
    w = np.minimum(w, max_weight)
    total = float(w.sum())
    if total > 0:
        w = w / total
    # One more clip in case renormalisation pushed something to the cap and
    # numerical rounding overshot.
    return np.minimum(w, max_weight)


def solve(
    req: PortfolioRequest,
    returns_matrix: npt.NDArray[np.float64],
) -> tuple[npt.NDArray[np.float64], dict[str, float | int | str]]:
    """Pure solver: returns (weights, diagnostics)."""
    _, cov = returns_stats(returns_matrix, shrink_covariance=req.shrink_covariance)
    vols = np.sqrt(np.diag(cov))
    # Guard against zero-variance assets — replace with the median vol so they
    # don't dominate the inverse weighting.
    if np.any(vols <= 0):
        median_vol = float(np.median(vols[vols > 0])) if np.any(vols > 0) else 1.0
        vols = np.where(vols > 0, vols, median_vol)
    inv_vol = 1.0 / vols
    weights = inv_vol / inv_vol.sum()
    if req.max_weight < 1.0:
        weights = _apply_max_weight_clip(weights, req.max_weight)
    return weights, {"solver": "closed-form", "status": "optimal", "iterations": 0}


def compute(
    req: PortfolioRequest,
    returns_matrix: npt.NDArray[np.float64],
    *,
    solver: str | None = None,  # accepted for runner signature compat; unused
) -> CalculatorResult:
    _ = solver
    started = time.perf_counter()
    try:
        weights, diag = solve(req, returns_matrix)
        mu, cov = returns_stats(
            returns_matrix, shrink_covariance=req.shrink_covariance
        )
        rc = risk_contributions(weights, cov)
        port_ret = portfolio_return(weights, mu)
        port_vol = portfolio_volatility(weights, cov)
        sharpe = (port_ret - req.risk_free_rate) / port_vol if port_vol > 0 else 0.0

        payload = PortfolioPayload(
            objective=PortfolioObjective.INVERSE_VOL,
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
            iterations=None,
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
                objective=PortfolioObjective.INVERSE_VOL,
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
