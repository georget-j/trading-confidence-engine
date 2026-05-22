"""Cornish-Fisher VaR.

Method #4 of the VaR cross-check. Parametric VaR adjusted for sample skew
and excess kurtosis using the Cornish-Fisher expansion:

    z_cf = z + (z² − 1) · S / 6
              + (z³ − 3z) · K / 24
              − (2z³ − 5z) · S² / 36

where z = Φ⁻¹(α), S = skew, K = excess kurtosis.

When the sample is exactly normal (S=K=0), Cornish-Fisher reduces to plain
parametric. On a fat-tailed sample (positive K, mild negative S — typical
equity returns) it gives a larger left-tail quantile than parametric,
bridging the gap to historical without abandoning the closed-form story.

Best used as the third independent estimator: parametric → cornish-fisher
→ historical. The progression itself is informative — wide gaps signal
non-normality, narrow gaps signal that returns look approximately Gaussian.
"""

from __future__ import annotations

import time

import numpy as np
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

CALCULATOR_ID = "cornish_fisher_var"
METHOD_NAME = "Cornish-Fisher (skew/kurtosis-adjusted parametric)"


def _cornish_fisher_z(z: float, skew: float, excess_kurt: float) -> float:
    """Apply the Cornish-Fisher correction to a standard-normal quantile."""
    return (
        z
        + (z * z - 1.0) * skew / 6.0
        + (z**3 - 3.0 * z) * excess_kurt / 24.0
        - (2.0 * z**3 - 5.0 * z) * skew * skew / 36.0
    )


def compute(req: VaRRequest, returns: list[float]) -> CalculatorResult:
    started = time.perf_counter()
    try:
        arr = to_returns_array(returns)
        mu = float(arr.mean())
        sigma = float(arr.std(ddof=1))
        skew = float(stats.skew(arr, bias=False))
        # Fisher=True returns *excess* kurtosis (i.e., 0 for normal).
        excess_kurt = float(stats.kurtosis(arr, fisher=True, bias=False))

        mu_h = horizon_scale_mean(mu, req.horizon_days)
        sigma_h = horizon_scale(sigma, req.horizon_days)

        alpha = 1.0 - req.confidence_level
        z = float(stats.norm.ppf(alpha))
        z_cf = _cornish_fisher_z(z, skew, excess_kurt)

        var_return = mu_h + sigma_h * z_cf
        var_loss = -var_return * req.portfolio_value

        # CVaR under Cornish-Fisher: there is no simple closed-form. The
        # cleanest approximation is to integrate the Cornish-Fisher-adjusted
        # density numerically over the tail. For the retail-grade signal we
        # need here, a coarser estimator suffices: scale the normal-CVaR /
        # normal-VaR ratio by the CF adjustment.
        # ψ = phi(z)/alpha is the normal lower-tail expectation factor.
        phi_z = float(stats.norm.pdf(z))
        # Standard normal CVaR-to-VaR ratio.
        cvar_norm_return = mu_h - sigma_h * (phi_z / alpha)
        # Tail-scaling factor: how much the CF tail extends beyond the normal one.
        # When z_cf and z have the same sign (typical for tail), the ratio is
        # well-defined; clip to a sane band [1.0, 5.0] to avoid pathological
        # behaviour on near-degenerate samples.
        tail_scale = max(1.0, min(5.0, abs(z_cf) / max(abs(z), 1e-9)))
        cvar_return = mu_h + (cvar_norm_return - mu_h) * tail_scale
        cvar_loss = -cvar_return * req.portfolio_value

        payload = VaRPayload(
            var_loss=max(var_loss, 0.0),
            cvar_loss=max(cvar_loss, 0.0),
            mean_return=mu_h,
            volatility=sigma_h,
            n_observations=int(arr.size),
            histogram_bins=None,
            var_return_quantile=float(var_return),
            cvar_return_quantile=float(cvar_return),
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


# Silence unused import warning when numpy is only used transitively via scipy.
_ = np
