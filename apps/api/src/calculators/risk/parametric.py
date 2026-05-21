"""Parametric (normal-assumption) VaR.

Method #2 of three. Closed-form under the assumption that daily returns are
N(μ, σ²). The standard formulae are:

    VaR_α  = -( μ + σ * Φ⁻¹(1-α) ) * portfolio_value
    CVaR_α = -( μ - σ * φ(Φ⁻¹(α)) / (1-α) ) * portfolio_value

Disagreement with the historical method is a useful signal: if they diverge,
real returns probably have fat tails or skew that the normal model misses.
"""

from __future__ import annotations

import time

from scipy import stats

from src.calculators.risk._common import (
    horizon_scale,
    horizon_scale_mean,
    to_returns_array,
)
from src.core.schemas import (
    CalculatorResult,
    VaRPayload,
    VaRRequest,
)

CALCULATOR_ID = "parametric_var"
METHOD_NAME = "Parametric (normal closed-form)"


def compute(req: VaRRequest, returns: list[float]) -> CalculatorResult:
    started = time.perf_counter()
    try:
        arr = to_returns_array(returns)
        mu = float(arr.mean())
        sigma = float(arr.std(ddof=1))

        # Scale to horizon (linear mean, sqrt(T) vol).
        mu_h = horizon_scale_mean(mu, req.horizon_days)
        sigma_h = horizon_scale(sigma, req.horizon_days)

        alpha = 1.0 - req.confidence_level  # tail probability
        z = float(stats.norm.ppf(alpha))     # negative for α<0.5
        # VaR loss (positive) = -(mu + sigma*z) * portfolio
        var_loss = -(mu_h + sigma_h * z) * req.portfolio_value

        # CVaR for normal: E[X | X < q] = mu - sigma * phi(z)/Phi(z)
        # where z = Phi^{-1}(alpha). phi/Phi at the lower tail.
        phi_z = float(stats.norm.pdf(z))
        cvar_return = mu_h - sigma_h * (phi_z / alpha)
        cvar_loss = -cvar_return * req.portfolio_value

        payload = VaRPayload(
            var_loss=max(var_loss, 0.0),
            cvar_loss=max(cvar_loss, 0.0),
            mean_return=mu_h,
            volatility=sigma_h,
            n_observations=int(arr.size),
            histogram_bins=None,
            var_return_quantile=None,
            cvar_return_quantile=None,
        )
        return CalculatorResult(
            calculator_id=CALCULATOR_ID,
            method_name=METHOD_NAME,
            payload=payload,
            duration_ms=(time.perf_counter() - started) * 1000.0,
            succeeded=True,
        )
    except Exception as exc:  # noqa: BLE001
        return CalculatorResult(
            calculator_id=CALCULATOR_ID,
            method_name=METHOD_NAME,
            payload=VaRPayload(
                var_loss=float("nan"), cvar_loss=float("nan"),
                mean_return=0.0, volatility=0.0, n_observations=0,
                histogram_bins=None, var_return_quantile=None, cvar_return_quantile=None,
            ),
            duration_ms=(time.perf_counter() - started) * 1000.0,
            succeeded=False,
            error=f"{type(exc).__name__}: {exc}",
        )
