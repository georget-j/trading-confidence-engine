"""Backtest performance metrics — Sharpe, Sortino, drawdown, Calmar, win rate."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from src.core.schemas import BacktestMetrics

TRADING_DAYS = 252


def compute_metrics(
    strategy_returns: npt.NDArray[np.float64],
    *,
    n_trades: int,
) -> BacktestMetrics:
    """All inputs are daily PnL fractions of the previous-day equity.

    The equity curve is the cumulative product of (1 + r). Metrics are
    annualised assuming 252 trading days.
    """
    if strategy_returns.size == 0:
        return BacktestMetrics(
            total_return=0.0,
            annualised_return=0.0,
            annualised_volatility=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            calmar_ratio=0.0,
            win_rate=0.0,
            n_trades=0,
        )

    equity = np.cumprod(1.0 + strategy_returns)
    total_return = float(equity[-1] - 1.0)

    n = strategy_returns.size
    years = n / TRADING_DAYS
    annualised_return = float((1.0 + total_return) ** (1.0 / max(years, 1e-9)) - 1.0)
    annualised_vol = float(strategy_returns.std(ddof=1) * np.sqrt(TRADING_DAYS)) if n > 1 else 0.0
    sharpe = annualised_return / annualised_vol if annualised_vol > 0 else 0.0

    # Max drawdown.
    peaks = np.maximum.accumulate(equity)
    drawdowns = (equity - peaks) / peaks
    max_dd = float(-drawdowns.min())

    calmar = annualised_return / max_dd if max_dd > 0 else 0.0
    win_rate = float(np.mean(strategy_returns > 0))

    return BacktestMetrics(
        total_return=total_return,
        annualised_return=annualised_return,
        annualised_volatility=annualised_vol,
        sharpe_ratio=sharpe,
        max_drawdown=max_dd,
        calmar_ratio=calmar,
        win_rate=win_rate,
        n_trades=n_trades,
    )
