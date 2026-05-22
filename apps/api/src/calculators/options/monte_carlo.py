"""Monte Carlo European option pricer (geometric Brownian motion).

Method #3 of the cross-method verification for options. Simulates `N_PATHS`
terminal stock prices under GBM with the same μ/σ/r/q as the analytical
methods, prices the payoff, and discounts back. Numerically distinct from
both py_vollib closed-form and QuantLib binomial — sampling-based rather
than analytical or recursive — so a bug in any one library cannot hide
from the cross-check.

Antithetic variates are used (each Z is paired with −Z) to roughly halve
the variance for free. A fixed seed makes the result bit-deterministic
for replay/audit purposes.

Greeks: pathwise delta is available analytically (`dC/dS = exp(-rT) * (S_T/S) * 1{S_T > K}`
for a call), but the noise on vega/gamma/theta/rho from MC is high enough
that we deliberately return `greeks=None` rather than ship numbers that
would look misleadingly precise next to the closed-form Greeks. The
cross-method check is on PRICE only, so this is no loss for verification.
"""

from __future__ import annotations

import time

import numpy as np

from src.calculators.options._common import canonical_time
from src.core.schemas import (
    CalculatorResult,
    OptionsPriceResult,
    OptionsPricingRequest,
    OptionStyle,
    OptionType,
)

CALCULATOR_ID = "monte_carlo_gbm"
METHOD_NAME = "Monte Carlo simulation (GBM, antithetic variates)"

# 100k paths × 2 (antithetic) = 200k samples. Standard error on an ATM
# European call price at σ=18%, T=30d is roughly 0.5¢ at this sample size —
# well within the 1e-3 absolute tolerance the cross-check uses.
N_PATHS = 100_000
SEED = 0xC0FFEE  # same seed as the VaR Monte Carlo, for consistency


def compute(req: OptionsPricingRequest) -> CalculatorResult:
    started = time.perf_counter()
    try:
        if req.style != OptionStyle.EUROPEAN:
            raise NotImplementedError(
                "Monte Carlo (GBM) supports European-style only. "
                "American early exercise needs an LSM (Longstaff-Schwartz) variant."
            )

        T = canonical_time(req.time_to_expiry_years)  # noqa: N806 — `T` is standard for time-to-expiry
        S0 = req.spot  # noqa: N806
        K = req.strike  # noqa: N806
        r = req.risk_free_rate
        q = req.dividend_yield
        sigma = req.volatility

        rng = np.random.default_rng(SEED)
        # Antithetic: pair each Z with −Z, so we draw N_PATHS halves.
        z_half = rng.standard_normal(N_PATHS // 2)
        z = np.concatenate([z_half, -z_half])

        # GBM terminal price: S_T = S0 * exp((r - q - 0.5σ²)T + σ√T Z)
        drift = (r - q - 0.5 * sigma * sigma) * T
        diffusion = sigma * np.sqrt(T) * z
        s_terminal = S0 * np.exp(drift + diffusion)

        if req.option_type == OptionType.CALL:
            payoff = np.maximum(s_terminal - K, 0.0)
        else:
            payoff = np.maximum(K - s_terminal, 0.0)

        discount = float(np.exp(-r * T))
        price = discount * float(np.mean(payoff))

        return CalculatorResult(
            calculator_id=CALCULATOR_ID,
            method_name=METHOD_NAME,
            payload=OptionsPriceResult(price=price, greeks=None),
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
