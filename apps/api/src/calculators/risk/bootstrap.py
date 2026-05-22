"""Bootstrap historical VaR.

Method #5 of the VaR cross-check. Resamples the historical returns with
replacement to construct an empirical distribution of the VaR quantile
estimate itself — useful both as an independent VaR estimate and (more
importantly) as a confidence interval on it.

The point estimate is the median quantile across `N_BOOTSTRAP` resamples,
which is more robust to outliers than the single-pass historical quantile
when the sample is small. The CVaR comes from the median tail-mean across
the same resamples.

This is genuinely independent from historical / parametric / Monte Carlo:
- historical uses the empirical CDF directly (one pass, no resampling)
- parametric assumes normality (closed-form)
- Monte Carlo assumes normality (simulation)
- bootstrap makes no distributional assumption AND captures sample uncertainty

A fixed seed makes the resampling deterministic for audit/replay.
"""

from __future__ import annotations

import time

import numpy as np

from src.calculators.risk._common import (
    horizon_scale_mean,
    to_returns_array,
)
from src.core.schemas import (
    CalculatorResult,
    VaRPayload,
    VaRRequest,
)

CALCULATOR_ID = "bootstrap_var"
METHOD_NAME = "Bootstrap historical (1000 resamples, fixed seed)"

# 1000 resamples is the textbook minimum for stable confidence intervals on
# tail quantiles. Higher would tighten the CI but adds runtime; 1000 is the
# right balance at the precision we report.
N_BOOTSTRAP = 1000
SEED = 0xBEEF1234


def compute(req: VaRRequest, returns: list[float]) -> CalculatorResult:
    started = time.perf_counter()
    try:
        arr = to_returns_array(returns)
        n = arr.size
        alpha = 1.0 - req.confidence_level
        rng = np.random.default_rng(SEED)

        # Resample-with-replacement, vectorised: build an (N_BOOTSTRAP, n)
        # matrix of indices then quantile across each row.
        idx = rng.integers(0, n, size=(N_BOOTSTRAP, n))
        samples = arr[idx]  # shape (N_BOOTSTRAP, n)

        # Per-sample VaR quantile.
        sample_quantiles = np.quantile(samples, alpha, axis=1)
        # Per-sample CVaR (mean of tail returns ≤ that sample's quantile).
        sample_cvars = np.empty(N_BOOTSTRAP)
        for i in range(N_BOOTSTRAP):
            tail = samples[i, samples[i] <= sample_quantiles[i]]
            sample_cvars[i] = tail.mean() if tail.size else sample_quantiles[i]

        # Point estimates: median across resamples (more robust than mean).
        daily_var_return = float(np.median(sample_quantiles))
        daily_cvar_return = float(np.median(sample_cvars))

        # Horizon scaling — same sqrt(T) convention as the other VaR methods.
        sqrt_t = float(np.sqrt(req.horizon_days))
        var_loss = -daily_var_return * sqrt_t * req.portfolio_value
        cvar_loss = -daily_cvar_return * sqrt_t * req.portfolio_value

        payload = VaRPayload(
            var_loss=max(var_loss, 0.0),
            cvar_loss=max(cvar_loss, 0.0),
            mean_return=horizon_scale_mean(float(arr.mean()), req.horizon_days),
            volatility=float(arr.std(ddof=1)) * sqrt_t,
            n_observations=int(arr.size),
            histogram_bins=None,
            var_return_quantile=daily_var_return,
            cvar_return_quantile=daily_cvar_return,
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
