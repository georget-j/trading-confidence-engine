"""Binomial-tree pricer via QuantLib (Leisen-Reimer, 801 steps).

Method #2 of the cross-method verification. Numerically distinct path from the
py_vollib closed-form, so an error in either library should be caught by the
disagreement. Leisen-Reimer is chosen over CRR because it converges much faster
for European vanillas (typically O(1/n^2) vs O(1/n)), giving ~1e-5 prices at
801 steps — tight enough to be meaningful as a cross-check.

Greeks are produced via finite differences (QuantLib exposes delta/gamma/theta
directly on the engine; vega/rho are bumped manually).
"""

from __future__ import annotations

import time

import QuantLib as ql  # noqa: N813 — `ql` is QuantLib's documented import alias

from src.calculators.options._common import canonical_days
from src.core.schemas import (
    CalculatorResult,
    GreeksPayload,
    OptionsPriceResult,
    OptionsPricingRequest,
    OptionStyle,
    OptionType,
)

CALCULATOR_ID = "quantlib_binomial_lr"
METHOD_NAME = "Leisen-Reimer binomial tree, 801 steps (QuantLib)"
STEPS = 801

_DAY_COUNT = ql.Actual365Fixed()
_CALENDAR = ql.NullCalendar()


def _build_process(
    spot: float, rate: float, dividend: float, vol: float, eval_date: ql.Date
) -> ql.BlackScholesMertonProcess:
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
    rate_handle = ql.YieldTermStructureHandle(ql.FlatForward(eval_date, rate, _DAY_COUNT))
    div_handle = ql.YieldTermStructureHandle(ql.FlatForward(eval_date, dividend, _DAY_COUNT))
    vol_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(eval_date, _CALENDAR, vol, _DAY_COUNT)
    )
    return ql.BlackScholesMertonProcess(spot_handle, div_handle, rate_handle, vol_handle)


def _payoff_and_exercise(
    req: OptionsPricingRequest, eval_date: ql.Date
) -> tuple[ql.PlainVanillaPayoff, ql.Exercise]:
    payoff = ql.PlainVanillaPayoff(
        ql.Option.Call if req.option_type == OptionType.CALL else ql.Option.Put,
        req.strike,
    )
    expiry = eval_date + canonical_days(req.time_to_expiry_years)
    exercise: ql.Exercise = (
        ql.EuropeanExercise(expiry)
        if req.style == OptionStyle.EUROPEAN
        else ql.AmericanExercise(eval_date, expiry)
    )
    return payoff, exercise


def _price_with_vol(req: OptionsPricingRequest, vol: float) -> float:
    """Recompute price with a bumped volatility (for vega via finite difference)."""
    eval_date = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = eval_date
    payoff, exercise = _payoff_and_exercise(req, eval_date)
    option = ql.VanillaOption(payoff, exercise)
    option.setPricingEngine(
        ql.BinomialVanillaEngine(
            _build_process(req.spot, req.risk_free_rate, req.dividend_yield, vol, eval_date),
            "lr",
            STEPS,
        )
    )
    return float(option.NPV())


def _price_with_rate(req: OptionsPricingRequest, rate: float) -> float:
    """Recompute price with a bumped risk-free rate (for rho via finite difference)."""
    eval_date = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = eval_date
    payoff, exercise = _payoff_and_exercise(req, eval_date)
    option = ql.VanillaOption(payoff, exercise)
    option.setPricingEngine(
        ql.BinomialVanillaEngine(
            _build_process(req.spot, rate, req.dividend_yield, req.volatility, eval_date),
            "lr",
            STEPS,
        )
    )
    return float(option.NPV())


def compute(req: OptionsPricingRequest) -> CalculatorResult:
    started = time.perf_counter()
    try:
        eval_date = ql.Date.todaysDate()
        ql.Settings.instance().evaluationDate = eval_date

        payoff, exercise = _payoff_and_exercise(req, eval_date)
        option = ql.VanillaOption(payoff, exercise)
        engine = ql.BinomialVanillaEngine(
            _build_process(
                req.spot, req.risk_free_rate, req.dividend_yield,
                req.volatility, eval_date,
            ),
            "lr",
            STEPS,
        )
        option.setPricingEngine(engine)

        price = float(option.NPV())
        delta = float(option.delta())
        gamma = float(option.gamma())
        # QuantLib theta is per-year; py_vollib's analytical theta is per-day. We
        # convert to per-day here so the two methods are comparable.
        theta = float(option.theta()) / 365.0

        # Vega via central difference (QuantLib's engine.vega() is unreliable for
        # binomial trees; finite diff is the standard fallback). Bump is 1pt vol.
        vol_bump = 0.01
        vega = (
            _price_with_vol(req, req.volatility + vol_bump)
            - _price_with_vol(req, req.volatility - vol_bump)
        ) / (2.0 * vol_bump) / 100.0  # per 1% vol move

        # Rho via central difference, bump 1bp rate.
        rate_bump = 0.0001
        rho = (
            _price_with_rate(req, req.risk_free_rate + rate_bump)
            - _price_with_rate(req, req.risk_free_rate - rate_bump)
        ) / (2.0 * rate_bump) / 100.0  # per 1% rate move

        greeks = GreeksPayload(
            delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho,
        )
        return CalculatorResult(
            calculator_id=CALCULATOR_ID,
            method_name=METHOD_NAME,
            payload=OptionsPriceResult(price=price, greeks=greeks),
            duration_ms=(time.perf_counter() - started) * 1000.0,
            succeeded=True,
        )
    except Exception as exc:  # noqa: BLE001
        return CalculatorResult(
            calculator_id=CALCULATOR_ID,
            method_name=METHOD_NAME,
            payload=OptionsPriceResult(price=float("nan")),
            duration_ms=(time.perf_counter() - started) * 1000.0,
            succeeded=False,
            error=f"{type(exc).__name__}: {exc}",
        )
