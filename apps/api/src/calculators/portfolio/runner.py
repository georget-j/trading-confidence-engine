"""Dispatch to the right portfolio optimizer based on the requested objective."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from src.calculators.portfolio import (
    inverse_vol,
    max_sharpe,
    mean_variance,
    min_variance,
    risk_parity,
)
from src.core.schemas import (
    CalculatorResult,
    PortfolioObjective,
    PortfolioRequest,
)


def optimize(
    req: PortfolioRequest,
    returns_matrix: npt.NDArray[np.float64],
    *,
    solver: str | None = None,
) -> CalculatorResult:
    if req.objective == PortfolioObjective.MEAN_VARIANCE:
        return mean_variance.compute(req, returns_matrix, solver=solver)
    if req.objective == PortfolioObjective.MAX_SHARPE:
        return max_sharpe.compute(req, returns_matrix, solver=solver)
    if req.objective == PortfolioObjective.RISK_PARITY:
        return risk_parity.compute(req, returns_matrix, solver=solver)
    if req.objective == PortfolioObjective.MIN_VARIANCE:
        return min_variance.compute(req, returns_matrix, solver=solver)
    if req.objective == PortfolioObjective.INVERSE_VOL:
        return inverse_vol.compute(req, returns_matrix, solver=solver)
    raise ValueError(f"Unknown objective: {req.objective}")
