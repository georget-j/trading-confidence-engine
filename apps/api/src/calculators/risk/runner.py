"""Runs the three VaR calculators in order."""

from __future__ import annotations

from src.calculators.risk import historical, monte_carlo, parametric
from src.core.schemas import CalculatorResult, VaRRequest


def run_var_calculators(
    req: VaRRequest, returns: list[float]
) -> list[CalculatorResult]:
    """Execute all three independent VaR methods.

    Returns is passed in by the orchestrator so the data provider (yfinance
    fetch, CSV, etc.) is a single dependency point — the calculators themselves
    are pure-numeric.
    """
    return [
        historical.compute(req, returns),
        parametric.compute(req, returns),
        monte_carlo.compute(req, returns),
    ]
