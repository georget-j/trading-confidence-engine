"""Backtest pipeline.

Stages: request → parse → resolve-data → calculate → verify → explain → respond
"""

from __future__ import annotations

import numpy as np

from src.calculators.backtest import run_backtest
from src.core.audit import new_audit_log, record
from src.core.schemas import (
    AuditLog,
    BacktestPayload,
    BacktestRequest,
    CalcFamily,
    CalculationRequest,
    FinalAnswer,
)
from src.data_providers import MarketDataProvider, default_provider
from src.scoring.backtest_confidence import score_backtest_verification
from src.verification.invariants_backtest import (
    check_backtest_invariants,
    check_walk_forward_reproducible,
    detect_lookahead,
)


def run_backtest_pipeline(
    request: CalculationRequest,
    bt_request: BacktestRequest,
    *,
    provider: MarketDataProvider | None = None,
) -> tuple[FinalAnswer, AuditLog]:
    log = new_audit_log(request.request_id)
    record(log, "request", request.model_dump(mode="json"))
    record(log, "parse", bt_request.model_dump(mode="json"))

    # ---- resolve data ----------------------------------------------------
    prov = provider or default_provider()
    returns_list = prov.fetch_daily_returns(bt_request.ticker, bt_request.lookback_days)
    returns = np.asarray(returns_list, dtype=np.float64)

    # ---- calculate -------------------------------------------------------
    result, equity, positions = run_backtest(bt_request, returns)
    record(log, "calculate", {"results": [result.model_dump(mode="json")]})

    # ---- verify ----------------------------------------------------------
    if not result.succeeded or not isinstance(result.payload, BacktestPayload):
        raise RuntimeError("Backtest failed; see audit log.")

    invariants = check_backtest_invariants(bt_request, equity, positions)
    reproducible = check_walk_forward_reproducible(bt_request, returns)
    lookahead_clean = detect_lookahead(bt_request, returns)

    # Slippage collapse: how much total return drops when we move from 0bp
    # to the largest sweep value.
    sweep = result.payload.slippage_sensitivity
    if len(sweep.total_return) >= 2 and sweep.total_return[0] != 0:
        best = max(sweep.total_return)
        worst = min(sweep.total_return)
        collapse = max(0.0, (best - worst) / (abs(best) + 1e-9))
    else:
        collapse = 0.0

    verification = score_backtest_verification(
        invariants=invariants,
        walk_forward_reproducible=reproducible,
        lookahead_clean=lookahead_clean,
        slippage_collapse=collapse,
        input_quality=1.0,
    )
    record(log, "verify", verification.model_dump(mode="json"))

    # Backfill the binary verification flags onto the payload.
    updated_payload = result.payload.model_copy(
        update={
            "walk_forward_reproducible": reproducible,
            "lookahead_clean": lookahead_clean,
        }
    )

    explanation = _build_explanation(bt_request, updated_payload, collapse)
    record(log, "explain", {"text": explanation})

    answer = FinalAnswer(
        request_id=request.request_id,
        family=CalcFamily.BACKTEST,
        verification_status=verification.overall_status,
        primary_result=updated_payload,
        calculator_results=[result.model_copy(update={"payload": updated_payload})],
        verification=verification,
        explanation=explanation,
        limitations=_limitations(verification, collapse, reproducible, lookahead_clean),
    )
    record(log, "respond", answer.model_dump(mode="json"))
    return answer, log


def _build_explanation(
    req: BacktestRequest, payload: BacktestPayload, collapse: float
) -> str:
    m = payload.metrics
    name = payload.strategy.value.replace("_", " ")
    extra = ""
    if payload.benchmark_metrics is not None:
        bh = payload.benchmark_metrics
        alpha = m.total_return - bh.total_return
        extra = (
            f" vs buy-and-hold {bh.total_return * 100:.1f}% "
            f"({'+' if alpha >= 0 else ''}{alpha * 100:.1f}pp alpha)"
        )
    return (
        f"{name.title()} on {req.ticker}: total return "
        f"{m.total_return * 100:.1f}% over {req.lookback_days} days{extra}. "
        f"Sharpe {m.sharpe_ratio:.2f}, max drawdown {m.max_drawdown * 100:.1f}%, "
        f"{m.n_trades} trades. "
        f"Slippage collapse: {collapse * 100:.0f}% across the sweep."
    )


def _limitations(
    verification: object, collapse: float, reproducible: bool, no_lookahead: bool
) -> list[str]:
    out: list[str] = [
        "Past performance does not predict future returns. In-sample "
        "backtests on a single ticker are particularly prone to over-fitting.",
        "Slippage and commission models are simplified (linear per trade); "
        "real execution costs depend on liquidity and order size.",
    ]
    if not reproducible:
        out.append(
            "Walk-forward reproducibility failed — running the backtest "
            "twice produced different equity curves. The engine has hidden "
            "state and the result cannot be trusted."
        )
    if not no_lookahead:
        out.append(
            "Look-ahead detector flagged the strategy: positions correlate "
            "with FUTURE returns more strongly than they do with present "
            "returns. The strategy is leaking information from the future."
        )
    if collapse > 0.10:
        out.append(
            f"PnL drops {collapse * 100:.0f}% between best- and worst-case "
            f"slippage assumptions. The strategy's edge is largely consumed "
            f"by trading frictions."
        )
    return out
