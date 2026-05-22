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

TRADING_DAYS = 252


def _downside_metrics(
    returns: np.ndarray,
) -> tuple[float | None, float | None, float | None]:
    """Compute (sortino_ratio, calmar_ratio, max_drawdown) from a daily-return
    series. All annualised. Returns (None, None, None) on degenerate inputs."""
    if returns.size < 30:
        return None, None, None

    mean_daily = float(returns.mean())
    annualised_return = mean_daily * TRADING_DAYS

    # Sortino: mean / downside deviation. Downside = returns below the mean
    # (Sortino's original formulation). Using zero as the threshold is a
    # common alternative but gives misleading values when most returns are
    # positive on average; we stick with mean-relative downside.
    downside = returns[returns < mean_daily] - mean_daily
    if downside.size == 0:
        return None, None, None
    downside_dev_daily = float(np.sqrt(np.mean(downside**2)))
    if downside_dev_daily <= 0:
        return None, None, None
    downside_dev_annual = downside_dev_daily * np.sqrt(TRADING_DAYS)
    sortino = annualised_return / downside_dev_annual

    # Calmar: annualised return / max drawdown of the cumulative-return series.
    cumulative = np.cumprod(1.0 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (running_max - cumulative) / running_max
    max_dd = float(np.max(drawdowns)) if drawdowns.size else 0.0
    if max_dd <= 1e-9:
        # Monotonic uptrend over the window — Calmar undefined.
        return float(sortino), None, 0.0
    calmar = annualised_return / max_dd
    return float(sortino), float(calmar), max_dd


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

        sortino, calmar, max_dd = _downside_metrics(arr)

        payload = VaRPayload(
            var_loss=max(var_loss, 0.0),
            cvar_loss=max(cvar_loss, 0.0),
            mean_return=horizon_scale_mean(float(arr.mean()), req.horizon_days),
            volatility=float(arr.std(ddof=1)) * sqrt_t,
            n_observations=int(arr.size),
            histogram_bins=_build_histogram(arr),
            var_return_quantile=daily_var_return,
            cvar_return_quantile=daily_cvar_return,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
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
