"""Runs the three VaR calculators in order."""

from __future__ import annotations

from src.calculators.risk import (
    bootstrap,
    cornish_fisher,
    historical,
    monte_carlo,
    parametric,
)
from src.core.schemas import CalculatorResult, VaRRequest


def run_var_calculators(
    req: VaRRequest, returns: list[float]
) -> list[CalculatorResult]:
    """Execute all five independent VaR methods.

    Returns is passed in by the orchestrator so the data provider (yfinance
    fetch, CSV, etc.) is a single dependency point — the calculators themselves
    are pure-numeric.

    Methods, in order of independence:
      1. Historical (empirical quantile) — no distributional assumption
      2. Parametric (normal closed-form) — assumes Gaussian returns
      3. Monte Carlo (normal-shock simulation) — sampling under Gaussian
      4. Cornish-Fisher (skew/kurt-adjusted parametric) — closed-form, distribution-aware
      5. Bootstrap historical (1000 resamples) — empirical, captures sample uncertainty
    """
    return [
        historical.compute(req, returns),
        parametric.compute(req, returns),
        monte_carlo.compute(req, returns),
        cornish_fisher.compute(req, returns),
        bootstrap.compute(req, returns),
    ]
