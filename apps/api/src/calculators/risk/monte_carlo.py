"""Monte Carlo VaR (normal-shock simulation).

Method #3 of three. Simulates `monte_carlo_paths` independent horizon paths
under a normal-return assumption with the same μ/σ as the historical sample.
Numerically distinct from parametric — uses sampling rather than closed-form —
which catches Monte Carlo bugs (seed mismanagement, biased sampling) that a
closed-form formula wouldn't expose.

A fixed seed is used so identical inputs always produce identical outputs;
this is a hard requirement for the audit log to be replayable.
"""

from __future__ import annotations

import time

import numpy as np

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

CALCULATOR_ID = "monte_carlo_var"
METHOD_NAME = "Monte Carlo (normal-shock simulation)"

MC_SEED = 0xC0FFEE  # deterministic for replayable audit logs


def compute(req: VaRRequest, returns: list[float]) -> CalculatorResult:
    started = time.perf_counter()
    try:
        arr = to_returns_array(returns)
        mu = float(arr.mean())
        sigma = float(arr.std(ddof=1))

        mu_h = horizon_scale_mean(mu, req.horizon_days)
        sigma_h = horizon_scale(sigma, req.horizon_days)

        rng = np.random.default_rng(MC_SEED)
        simulated = rng.normal(mu_h, sigma_h, size=req.monte_carlo_paths)

        alpha = 1.0 - req.confidence_level
        sim_var_return = float(np.quantile(simulated, alpha))
        tail = simulated[simulated <= sim_var_return]
        sim_cvar_return = float(tail.mean()) if tail.size else sim_var_return

        var_loss = -sim_var_return * req.portfolio_value
        cvar_loss = -sim_cvar_return * req.portfolio_value

        payload = VaRPayload(
            var_loss=max(var_loss, 0.0),
            cvar_loss=max(cvar_loss, 0.0),
            mean_return=mu_h,
            volatility=sigma_h,
            n_observations=int(arr.size),
            histogram_bins=None,
            var_return_quantile=None,
            cvar_return_quantile=None,
            sortino_ratio=None,
            calmar_ratio=None,
            max_drawdown=None,
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
                sortino_ratio=None, calmar_ratio=None, max_drawdown=None,
            ),
            duration_ms=(time.perf_counter() - started) * 1000.0,
            succeeded=False,
            error=f"{type(exc).__name__}: {exc}",
        )
