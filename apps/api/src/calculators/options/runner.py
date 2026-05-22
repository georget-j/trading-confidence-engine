"""Runs both options calculators and returns their results in order."""

from __future__ import annotations

from src.calculators.options import binomial, black_scholes, crank_nicolson, monte_carlo
from src.core.schemas import CalculatorResult, OptionsPricingRequest


def run_options_calculators(req: OptionsPricingRequest) -> list[CalculatorResult]:
    """Execute every independent options calculator we have.

    Order is significant: the first successful result becomes the primary
    result returned to the user. The verifier compares all of them.

    Four independent methods:
      1. Black-Scholes-Merton closed-form (py_vollib) — analytical
      2. Leisen-Reimer binomial tree, 801 steps (QuantLib) — lattice
      3. Monte Carlo simulation, 100k antithetic paths — sampling
      4. Crank-Nicolson finite-difference (BS PDE) — implicit grid solver
    """
    return [
        black_scholes.compute(req),
        binomial.compute(req),
        monte_carlo.compute(req),
        crank_nicolson.compute(req),
    ]
