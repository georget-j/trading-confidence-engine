"""Tests for the Mean-reversion + Bollinger Band backtest strategies."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest

from src.calculators.backtest import strategies_extra
from src.calculators.backtest.runner import run_backtest
from src.core.schemas import BacktestRequest, BacktestStrategy


def _normal_returns(n: int = 504, seed: int = 42) -> npt.NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    return rng.normal(0.0003, 0.012, size=n)


# ---- Mean reversion ---------------------------------------------------------


def test_mean_reversion_positions_are_zero_or_one() -> None:
    returns = _normal_returns()
    positions = strategies_extra.mean_reversion(returns, lookback=20, entry_z=1.5)
    unique = set(np.unique(positions).tolist())
    assert unique <= {0.0, 1.0}, f"unexpected positions: {unique}"


def test_mean_reversion_no_lookahead() -> None:
    """positions[t] must only depend on returns[:t] — never on returns[t:].

    Verify by perturbing future-only returns and confirming positions are unchanged.
    """
    returns = _normal_returns()
    base_positions = strategies_extra.mean_reversion(returns.copy(), 20, 1.5)
    half = len(returns) // 2
    perturbed = returns.copy()
    rng = np.random.default_rng(99)
    perturbed[half:] = rng.normal(0.0003, 0.012, size=len(returns) - half)
    new_positions = strategies_extra.mean_reversion(perturbed, 20, 1.5)
    # The first half of positions must be identical (they only see returns[:half]).
    assert np.array_equal(base_positions[:half], new_positions[:half])


def test_mean_reversion_warmup_is_flat() -> None:
    """positions[0 : lookback] must all be 0 — not enough history to compute z-score."""
    returns = _normal_returns()
    positions = strategies_extra.mean_reversion(returns, lookback=30, entry_z=1.5)
    assert np.all(positions[:30] == 0.0)


# ---- Bollinger Bands --------------------------------------------------------


def test_bollinger_positions_are_zero_or_one() -> None:
    returns = _normal_returns()
    positions = strategies_extra.bollinger(returns, lookback=20, mult=2.0)
    unique = set(np.unique(positions).tolist())
    assert unique <= {0.0, 1.0}


def test_bollinger_no_lookahead() -> None:
    returns = _normal_returns()
    base = strategies_extra.bollinger(returns.copy(), 20, 2.0)
    half = len(returns) // 2
    perturbed = returns.copy()
    rng = np.random.default_rng(99)
    perturbed[half:] = rng.normal(0.0003, 0.012, size=len(returns) - half)
    new = strategies_extra.bollinger(perturbed, 20, 2.0)
    assert np.array_equal(base[:half], new[:half])


def test_bollinger_tighter_band_triggers_more_trades() -> None:
    """Smaller mult → narrower band → more long-entry signals → more trades."""
    returns = _normal_returns()
    wide = strategies_extra.bollinger(returns, lookback=20, mult=3.0)
    narrow = strategies_extra.bollinger(returns, lookback=20, mult=1.5)
    trades_wide = int(np.sum(np.abs(np.diff(wide))))
    trades_narrow = int(np.sum(np.abs(np.diff(narrow))))
    assert trades_narrow >= trades_wide


# ---- Runner integration -----------------------------------------------------


@pytest.mark.parametrize(
    "strategy",
    [BacktestStrategy.MEAN_REVERSION, BacktestStrategy.BOLLINGER],
)
def test_runner_dispatches_new_strategy(strategy: BacktestStrategy) -> None:
    returns = _normal_returns()
    req = BacktestRequest(
        ticker="TEST", lookback_days=504, strategy=strategy,
        initial_capital=10_000.0,
    )
    result, _equity, _positions = run_backtest(req, returns)
    assert result.succeeded, result.error
    assert result.payload.strategy == strategy
    # Benchmark metrics filled in (buy-and-hold reference) for non-BH strategies.
    assert result.payload.benchmark_metrics is not None
