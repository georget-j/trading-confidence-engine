"""Historical (empirical-quantile) VaR.

Method #1 of three. Uses the empirical distribution of returns directly — no
distributional assumption. Disadvantage: only captures losses seen in the
sample (so VaR_99 with 252 days has only ~2-3 data points).
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
    HistogramBin,
    VaRPayload,
    VaRRequest,
)

# Number of histogram bars to surface in the API response. 30 reads well at
# typical desktop chart widths without losing fat-tail detail.
HISTOGRAM_BINS = 30


def _build_histogram(returns: np.ndarray) -> list[HistogramBin]:
    counts, edges = np.histogram(returns, bins=HISTOGRAM_BINS)
    return [
        HistogramBin(bin_min=float(edges[i]), bin_max=float(edges[i + 1]), count=int(counts[i]))
        for i in range(len(counts))
    ]

CALCULATOR_ID = "historical_var"
METHOD_NAME = "Historical (empirical quantile)"


def compute(req: VaRRequest, returns: list[float]) -> CalculatorResult:
    started = time.perf_counter()
    try:
        arr = to_returns_array(returns)

        # Daily VaR at the chosen confidence level. The (1 - alpha) tail.
        alpha = 1.0 - req.confidence_level
        daily_var_return = float(np.quantile(arr, alpha))

        # Empirical CVaR (Expected Shortfall): mean of returns below VaR quantile.
        tail = arr[arr <= daily_var_return]
        daily_cvar_return = float(tail.mean()) if tail.size else daily_var_return

        # Horizon scaling — for historical we scale the loss quantile by sqrt(T)
        # (standard practice; assumes returns are iid which is the same caveat
        # as parametric).
        sqrt_t = float(np.sqrt(req.horizon_days))
        var_loss = -daily_var_return * sqrt_t * req.portfolio_value
        cvar_loss = -daily_cvar_return * sqrt_t * req.portfolio_value

        payload = VaRPayload(
            var_loss=max(var_loss, 0.0),
            cvar_loss=max(cvar_loss, 0.0),
            mean_return=horizon_scale_mean(float(arr.mean()), req.horizon_days),
            volatility=float(arr.std(ddof=1)) * sqrt_t,
            n_observations=int(arr.size),
            histogram_bins=_build_histogram(arr),
            var_return_quantile=daily_var_return,
            cvar_return_quantile=daily_cvar_return,
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
