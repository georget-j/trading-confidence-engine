"""Runs both options calculators and returns their results in order."""

from __future__ import annotations

from src.calculators.options import binomial, black_scholes
from src.core.schemas import CalculatorResult, OptionsPricingRequest


def run_options_calculators(req: OptionsPricingRequest) -> list[CalculatorResult]:
    """Execute every independent options calculator we have.

    Order is significant: the first successful result becomes the primary
    result returned to the user. The verifier compares all of them.
    """
    return [
        black_scholes.compute(req),
        binomial.compute(req),
    ]
