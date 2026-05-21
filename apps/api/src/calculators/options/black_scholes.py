"""Closed-form Black-Scholes via py_vollib.

This is method #1 of the cross-method verification. Independent from QuantLib's
binomial implementation — they share Black-Scholes assumptions but use different
codebases, so a bug in one library is unlikely to also exist in the other.
"""

from __future__ import annotations

import time

from py_vollib.black_scholes_merton import black_scholes_merton
from py_vollib.black_scholes_merton.greeks.analytical import (
    delta as bsm_delta,
)
from py_vollib.black_scholes_merton.greeks.analytical import (
    gamma as bsm_gamma,
)
from py_vollib.black_scholes_merton.greeks.analytical import (
    rho as bsm_rho,
)
from py_vollib.black_scholes_merton.greeks.analytical import (
    theta as bsm_theta,
)
from py_vollib.black_scholes_merton.greeks.analytical import (
    vega as bsm_vega,
)

from src.calculators.options._common import canonical_time
from src.core.schemas import (
    CalculatorResult,
    GreeksPayload,
    OptionsPriceResult,
    OptionsPricingRequest,
    OptionStyle,
    OptionType,
)

CALCULATOR_ID = "py_vollib_bsm_closed_form"
METHOD_NAME = "Black-Scholes-Merton closed-form (py_vollib)"


def _flag(option_type: OptionType) -> str:
    return "c" if option_type == OptionType.CALL else "p"


def compute(req: OptionsPricingRequest) -> CalculatorResult:
    """Price + Greeks via py_vollib closed-form Black-Scholes-Merton."""
    started = time.perf_counter()
    try:
        if req.style != OptionStyle.EUROPEAN:
            raise NotImplementedError(
                "py_vollib closed-form supports European-style only."
            )
        flag = _flag(req.option_type)
        # Day-rounded T — matches what QuantLib will price.
        T = canonical_time(req.time_to_expiry_years)  # noqa: N806 — `T` is standard for time-to-expiry
        price = black_scholes_merton(
            flag, req.spot, req.strike, T,
            req.risk_free_rate, req.volatility, req.dividend_yield,
        )
        greeks = GreeksPayload(
            delta=bsm_delta(flag, req.spot, req.strike, T,
                            req.risk_free_rate, req.volatility, req.dividend_yield),
            gamma=bsm_gamma(flag, req.spot, req.strike, T,
                            req.risk_free_rate, req.volatility, req.dividend_yield),
            vega=bsm_vega(flag, req.spot, req.strike, T,
                          req.risk_free_rate, req.volatility, req.dividend_yield),
            theta=bsm_theta(flag, req.spot, req.strike, T,
                            req.risk_free_rate, req.volatility, req.dividend_yield),
            rho=bsm_rho(flag, req.spot, req.strike, T,
                        req.risk_free_rate, req.volatility, req.dividend_yield),
        )
        return CalculatorResult(
            calculator_id=CALCULATOR_ID,
            method_name=METHOD_NAME,
            payload=OptionsPriceResult(price=float(price), greeks=greeks),
            duration_ms=(time.perf_counter() - started) * 1000.0,
            succeeded=True,
        )
    except Exception as exc:  # noqa: BLE001 — surfaced via succeeded=False
        return CalculatorResult(
            calculator_id=CALCULATOR_ID,
            method_name=METHOD_NAME,
            payload=OptionsPriceResult(price=float("nan")),
            duration_ms=(time.perf_counter() - started) * 1000.0,
            succeeded=False,
            error=f"{type(exc).__name__}: {exc}",
        )
