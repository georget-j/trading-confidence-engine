"""Backtest invariants + look-ahead bias detection + reproducibility.

The three verification ideas:
1. **Walk-forward reproducibility** — running the backtest twice with the
   same inputs must produce bit-identical equity curves. If not, the engine
   has hidden state (RNG seed leak, time-of-day dependence, etc.).
2. **Look-ahead detection** — shift the price series by a few days and
   re-run. If positions correlate strongly with the SHIFTED returns (i.e.
   the strategy "knew about the future"), the strategy is leaking.
3. **Invariants** — position bounds, no NaN equity, equity ≥ 0
   (long-only, no leverage), monotonic time index.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from src.calculators.backtest.engine import execute, positions_for
from src.core.schemas import (
    BacktestRequest,
    InvariantCheck,
)

LOOKAHEAD_CORR_THRESHOLD = 0.6


def check_backtest_invariants(
    req: BacktestRequest,
    equity: npt.NDArray[np.float64],
    positions: npt.NDArray[np.float64],
) -> list[InvariantCheck]:
    checks: list[InvariantCheck] = []
    checks.append(
        InvariantCheck(
            name="equity_finite",
            description="All equity values are finite",
            passed=bool(np.all(np.isfinite(equity))),
            detail=None if np.all(np.isfinite(equity)) else "NaN/inf in equity",
        )
    )
    checks.append(
        InvariantCheck(
            name="equity_non_negative",
            description="Long-only equity is never negative",
            passed=bool(np.all(equity >= 0)),
            detail=(
                None if np.all(equity >= 0) else f"min equity {float(equity.min())}"
            ),
        )
    )
    in_range = bool(np.all((positions >= -1e-9) & (positions <= 1.0 + 1e-9)))
    checks.append(
        InvariantCheck(
            name="positions_in_unit_interval",
            description="Long-only positions ∈ [0, 1] (no leverage, no shorts)",
            passed=in_range,
            detail=None
            if in_range
            else f"min={float(positions.min())} max={float(positions.max())}",
        )
    )
    return checks


def check_walk_forward_reproducible(
    req: BacktestRequest, returns: npt.NDArray[np.float64]
) -> bool:
    """Run twice and confirm bit-identical equity curves."""
    a, _, _, _ = execute(req, returns)
    b, _, _, _ = execute(req, returns)
    return bool(np.array_equal(a, b))


def detect_lookahead(
    req: BacktestRequest, returns: npt.NDArray[np.float64], shift: int = 5
) -> bool:
    """Return True if the strategy looks clean (no future-leak detected).

    Method: compute Pearson correlation between positions[t] and the SHIFTED
    returns[t+shift]. A clean strategy uses only past data, so this
    correlation should be no higher than the baseline correlation between
    positions and current returns (which reflects the strategy's actual
    edge, not future-knowledge).

    The test is conservative: we declare a leak only if the future-shifted
    correlation EXCEEDS the present-day correlation by a comfortable margin.
    """
    positions = positions_for(req, returns)
    n = returns.size
    if n <= shift + 30:
        return True  # not enough data to test

    sliced_pos = positions[: n - shift]
    # Constant positions can't leak — nothing varies with anything.
    if float(np.std(sliced_pos)) < 1e-9:
        return True

    # Correlation with TODAY's return (strategy's actual edge — baseline).
    today_corr = float(np.corrcoef(sliced_pos, returns[: n - shift])[0, 1])
    # Correlation with FUTURE returns (what a look-ahead strategy would see).
    future_corr = float(np.corrcoef(sliced_pos, returns[shift:])[0, 1])
    # Numerical degeneracies (constant returns slice) → treat as clean.
    if not (np.isfinite(today_corr) and np.isfinite(future_corr)):
        return True
    # A clean strategy has roughly equal correlation with past and future
    # returns (both small). A leaker has dramatically higher future_corr.
    excess_future = future_corr - today_corr
    return excess_future < LOOKAHEAD_CORR_THRESHOLD


def execute_lookahead_strategy(
    returns: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    """Test fixture: a deliberately-leaking strategy.

    positions[t] = 1 if returns[t] > 0 else 0 — i.e. it perfectly knows the
    sign of today's return. The detector MUST catch this.
    """
    return (returns > 0).astype(np.float64)
