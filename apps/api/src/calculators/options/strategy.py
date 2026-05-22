"""Multi-leg options strategy pricing.

Reuses the existing single-leg pricers (BSM closed-form, QuantLib binomial)
on each leg, then aggregates into a strategy-level payload. No new pricing
math — the verification machinery applies per-leg via the cross-method
checker, and the aggregate `net_premium` is what the user sees.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from src.calculators.options import binomial, black_scholes
from src.core.schemas import (
    CalculatorResult,
    GreeksPayload,
    OptionsPriceResult,
    OptionsPricingRequest,
    OptionsStrategyPayload,
    OptionsStrategyRequest,
    StrategyLeg,
    StrategyLegResult,
)

# Per-method identifiers — distinct from single-leg ones so the audit log
# makes it obvious which path produced a result.
BSM_CALCULATOR_ID = "py_vollib_bsm_strategy"
BSM_METHOD_NAME = "BSM strategy (py_vollib per leg)"

BINOMIAL_CALCULATOR_ID = "quantlib_binomial_strategy"
BINOMIAL_METHOD_NAME = "Binomial strategy (QuantLib per leg)"


# Type alias for the single-leg pricers we delegate to.
_SingleLegCompute = Callable[[OptionsPricingRequest], CalculatorResult]


def _leg_to_single_request(
    strategy: OptionsStrategyRequest, leg: StrategyLeg
) -> OptionsPricingRequest:
    return OptionsPricingRequest(
        spot=strategy.spot,
        strike=leg.strike,
        time_to_expiry_years=leg.time_to_expiry_years,
        volatility=leg.volatility,
        risk_free_rate=strategy.risk_free_rate,
        dividend_yield=strategy.dividend_yield,
        option_type=leg.option_type,
        style=strategy.style,
    )


def _compute_via_method(
    req: OptionsStrategyRequest,
    *,
    calculator_id: str,
    method_name: str,
    single_leg_compute: _SingleLegCompute,
) -> CalculatorResult:
    """Price every leg via `single_leg_compute`, aggregate net premium + Greeks.

    If any leg fails to price, the whole strategy result is marked failed —
    a partial answer would be more confusing than useful.
    """
    started = time.perf_counter()
    leg_results: list[StrategyLegResult] = []
    net_premium = 0.0
    net_delta = 0.0
    net_gamma = 0.0
    net_vega = 0.0
    net_theta = 0.0
    net_rho = 0.0

    for leg in req.legs:
        single_req = _leg_to_single_request(req, leg)
        single = single_leg_compute(single_req)
        if not single.succeeded or not isinstance(single.payload, OptionsPriceResult):
            return CalculatorResult(
                calculator_id=calculator_id,
                method_name=method_name,
                payload=OptionsStrategyPayload(
                    legs=[],
                    net_premium=float("nan"),
                    net_greeks=GreeksPayload(
                        delta=0.0, gamma=0.0, vega=0.0, theta=0.0, rho=0.0
                    ),
                ),
                duration_ms=(time.perf_counter() - started) * 1000.0,
                succeeded=False,
                error=single.error or "Leg pricing failed.",
            )

        leg_price = single.payload.price
        leg_greeks = single.payload.greeks
        leg_results.append(
            StrategyLegResult(
                option_type=leg.option_type,
                strike=leg.strike,
                quantity=leg.quantity,
                time_to_expiry_years=leg.time_to_expiry_years,
                volatility=leg.volatility,
                price=leg_price,
                greeks=leg_greeks,
            )
        )
        net_premium += leg.quantity * leg_price
        if leg_greeks is not None:
            net_delta += leg.quantity * leg_greeks.delta
            net_gamma += leg.quantity * leg_greeks.gamma
            net_vega += leg.quantity * leg_greeks.vega
            net_theta += leg.quantity * leg_greeks.theta
            net_rho += leg.quantity * leg_greeks.rho

    return CalculatorResult(
        calculator_id=calculator_id,
        method_name=method_name,
        payload=OptionsStrategyPayload(
            legs=leg_results,
            net_premium=net_premium,
            net_greeks=GreeksPayload(
                delta=net_delta,
                gamma=net_gamma,
                vega=net_vega,
                theta=net_theta,
                rho=net_rho,
            ),
        ),
        duration_ms=(time.perf_counter() - started) * 1000.0,
        succeeded=True,
    )


def compute_bsm(req: OptionsStrategyRequest) -> CalculatorResult:
    """Price the strategy via per-leg Black-Scholes-Merton (py_vollib)."""
    return _compute_via_method(
        req,
        calculator_id=BSM_CALCULATOR_ID,
        method_name=BSM_METHOD_NAME,
        single_leg_compute=black_scholes.compute,
    )


def compute_binomial(req: OptionsStrategyRequest) -> CalculatorResult:
    """Price the strategy via per-leg QuantLib binomial tree."""
    return _compute_via_method(
        req,
        calculator_id=BINOMIAL_CALCULATOR_ID,
        method_name=BINOMIAL_METHOD_NAME,
        single_leg_compute=binomial.compute,
    )


def run_strategy_calculators(req: OptionsStrategyRequest) -> list[CalculatorResult]:
    """Both methods, in order. BSM result is the primary for display."""
    return [compute_bsm(req), compute_binomial(req)]
