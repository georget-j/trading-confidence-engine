"""Top-level backtest entrypoint — runs the strategy, captures the slippage
sweep, builds the metrics, returns a CalculatorResult.
"""

from __future__ import annotations

import time

import numpy as np
import numpy.typing as npt

from src.calculators.backtest.engine import execute
from src.calculators.backtest.metrics import compute_metrics
from src.core.schemas import (
    BacktestPayload,
    BacktestRequest,
    BacktestStrategy,
    CalculatorResult,
    EquityPoint,
    SlippageSensitivity,
)

CALCULATOR_ID = "backtest_engine"
SLIPPAGE_SWEEP_BPS = [0.0, 5.0, 10.0, 20.0, 50.0]


def _method_name(strategy: BacktestStrategy) -> str:
    return {
        BacktestStrategy.BUY_AND_HOLD: "Buy-and-hold",
        BacktestStrategy.MA_CROSSOVER: "Moving-average crossover",
        BacktestStrategy.MOMENTUM: "Momentum (trailing return)",
        BacktestStrategy.MEAN_REVERSION: "Mean reversion (z-score)",
        BacktestStrategy.BOLLINGER: "Bollinger Bands",
    }[strategy]


def run_backtest(
    req: BacktestRequest,
    returns: npt.NDArray[np.float64],
) -> tuple[CalculatorResult, npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Returns (result, equity_curve, positions). The latter two are exposed
    so the pipeline can verify them without re-running."""
    started = time.perf_counter()
    try:
        equity, strat_returns, positions, n_trades = execute(req, returns)
        metrics = compute_metrics(strat_returns, n_trades=n_trades)

        # Slippage sensitivity sweep.
        sweep_returns: list[float] = []
        for bps in SLIPPAGE_SWEEP_BPS:
            eq_swp, _, _, _ = execute(req, returns, slippage_bps=bps)
            sweep_returns.append(float(eq_swp[-1] / req.initial_capital - 1.0))
        slippage = SlippageSensitivity(
            bps=list(SLIPPAGE_SWEEP_BPS), total_return=sweep_returns
        )

        # Benchmark (buy-and-hold) on the same data, when not already BH.
        benchmark_metrics = None
        if req.strategy != BacktestStrategy.BUY_AND_HOLD:
            bh_req = req.model_copy(update={"strategy": BacktestStrategy.BUY_AND_HOLD})
            _, bh_returns, _, bh_trades = execute(bh_req, returns)
            benchmark_metrics = compute_metrics(bh_returns, n_trades=bh_trades)

        # Sample the equity curve down to ~150 points for the chart.
        n_points = min(len(equity), 150)
        step = max(1, len(equity) // n_points)
        curve = [
            EquityPoint(day_index=int(i), equity=float(equity[i]), position=float(positions[i]))
            for i in range(0, len(equity), step)
        ]

        payload = BacktestPayload(
            kind="backtest",
            strategy=req.strategy,
            ticker=req.ticker,
            metrics=metrics,
            benchmark_metrics=benchmark_metrics,
            equity_curve=curve,
            slippage_sensitivity=slippage,
            walk_forward_reproducible=True,  # filled in by the pipeline
            lookahead_clean=True,  # filled in by the pipeline
        )
        return (
            CalculatorResult(
                calculator_id=CALCULATOR_ID,
                method_name=_method_name(req.strategy),
                payload=payload,
                duration_ms=(time.perf_counter() - started) * 1000.0,
                succeeded=True,
            ),
            equity,
            positions,
        )
    except Exception as exc:  # noqa: BLE001
        # Build an empty payload so the type checks pass.
        from src.core.schemas import BacktestMetrics

        empty_metrics = BacktestMetrics(
            total_return=float("nan"), annualised_return=float("nan"),
            annualised_volatility=float("nan"), sharpe_ratio=float("nan"),
            max_drawdown=float("nan"), calmar_ratio=float("nan"),
            win_rate=float("nan"), n_trades=0,
        )
        return (
            CalculatorResult(
                calculator_id=CALCULATOR_ID,
                method_name=_method_name(req.strategy),
                payload=BacktestPayload(
                    strategy=req.strategy, ticker=req.ticker,
                    metrics=empty_metrics, benchmark_metrics=None,
                    equity_curve=[],
                    slippage_sensitivity=SlippageSensitivity(bps=[], total_return=[]),
                    walk_forward_reproducible=False, lookahead_clean=False,
                ),
                duration_ms=(time.perf_counter() - started) * 1000.0,
                succeeded=False,
                error=f"{type(exc).__name__}: {exc}",
            ),
            np.zeros(0),
            np.zeros(0),
        )
