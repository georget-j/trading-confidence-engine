"""Sensitivity analysis for portfolio optimization.

Convex optimization gives a single optimal solution per problem, so cross-method
agreement (the V1/V5 story) doesn't apply directly. What DOES distinguish a
trustworthy portfolio from a fragile one is **stability under small input
perturbations**.

We re-solve the problem with each expected-return component bumped by ±1% (a
common econometric noise scale on annualised means), then measure the
maximum weight movement across all perturbed solutions. A stable solution
shifts by basis points; a fragile one swings 50 percentage points.

This becomes the `instability_score`:
    0.0 = perfectly stable (all weights within 1pp of the base solution)
    1.0 = catastrophically unstable (a weight moved >25pp under a 1% input bump)
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from src.calculators.portfolio import max_sharpe, mean_variance, risk_parity
from src.core.schemas import PortfolioObjective, PortfolioRequest

# 1% relative bumps on each μ_i, one at a time and one at a time downwards.
DEFAULT_BUMP = 0.01
# A weight move of 25 percentage points under a 1% input bump caps out the score.
MAX_MEANINGFUL_MOVE = 0.25


def compute_instability(
    req: PortfolioRequest,
    returns_matrix: npt.NDArray[np.float64],
    base_weights: npt.NDArray[np.float64],
    *,
    bump: float = DEFAULT_BUMP,
) -> tuple[float, dict[str, float]]:
    """Return (instability_score in [0, 1], diagnostics dict).

    Strategy: shift the entire returns series for each asset by ±bump on the
    daily mean (equivalent to perturbing the estimated μ by bump in
    annualised space, since μ_annual = mean·252). Re-solve, record the max
    absolute weight delta across all perturbations.
    """
    n = returns_matrix.shape[1]
    mean_daily = returns_matrix.mean(axis=0)
    # Daily bump that produces a `bump`-relative shift in annualised mean.
    # Annualised μ = mean·252, so to shift μ by bump·μ we shift mean by the
    # same fraction.
    max_move = 0.0
    for i in range(n):
        for direction in (1.0, -1.0):
            perturbed = returns_matrix.copy()
            shift = direction * bump * abs(mean_daily[i] if mean_daily[i] != 0 else 1e-4)
            perturbed[:, i] = perturbed[:, i] + shift
            try:
                if req.objective == PortfolioObjective.MEAN_VARIANCE:
                    new_w, _ = mean_variance.solve(req, perturbed)
                elif req.objective == PortfolioObjective.MAX_SHARPE:
                    new_w, _ = max_sharpe.solve(req, perturbed)
                else:  # RISK_PARITY — μ-invariant, so this perturbation
                    # primarily probes covariance noise sensitivity.
                    new_w, _ = risk_parity.solve(req, perturbed)
            except Exception:  # noqa: BLE001 — instability counts as movement
                return 1.0, {"failed_at_asset": float(i), "direction": direction}
            move = float(np.max(np.abs(new_w - base_weights)))
            max_move = max(max_move, move)

    score = min(max_move / MAX_MEANINGFUL_MOVE, 1.0)
    return score, {"max_weight_move": max_move, "bump_size": bump}
