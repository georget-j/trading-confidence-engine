"""Backtest execution loop.

The engine is intentionally simple and explicit so the look-ahead detector
has somewhere to attach itself:

    For each day t:
        - position[t] was chosen using returns[:t]
        - if position changed since t-1, charge slippage on the change
        - strategy PnL = position[t] * underlying_return[t]
        - subtract slippage_bps × |Δposition| × 1e-4 from PnL
        - update equity

A "trade" is any day where the position changes.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from src.calculators.backtest import strategies
from src.core.schemas import BacktestRequest, BacktestStrategy


def positions_for(
    req: BacktestRequest, returns: npt.NDArray[np.float64]
) -> npt.NDArray[np.float64]:
    """Dispatch to the right strategy signal generator."""
    if req.strategy == BacktestStrategy.BUY_AND_HOLD:
        return strategies.buy_and_hold(returns)
    if req.strategy == BacktestStrategy.MA_CROSSOVER:
        return strategies.ma_crossover(returns, req.ma_fast, req.ma_slow)
    if req.strategy == BacktestStrategy.MOMENTUM:
        return strategies.momentum(returns, req.momentum_lookback)
    raise ValueError(f"Unknown strategy: {req.strategy}")


def execute(
    req: BacktestRequest,
    returns: npt.NDArray[np.float64],
    *,
    slippage_bps: float | None = None,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64], int]:
    """Returns (equity_curve, strategy_returns, positions, n_trades).

    `slippage_bps` overrides req.slippage_bps when set — used by the
    sensitivity sweep.
    """
    bps = slippage_bps if slippage_bps is not None else req.slippage_bps
    positions = positions_for(req, returns)

    # Slippage charged on absolute position change.
    pos_change = np.zeros_like(positions)
    pos_change[1:] = np.abs(np.diff(positions))
    slippage_cost = pos_change * (bps * 1e-4)

    strategy_returns = positions * returns - slippage_cost
    equity = (req.initial_capital * np.cumprod(1.0 + strategy_returns)).astype(
        np.float64
    )
    n_trades = int(np.sum(pos_change > 0))
    return equity, strategy_returns, positions, n_trades
