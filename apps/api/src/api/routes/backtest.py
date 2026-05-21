"""Backtest routes (V7)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.core.schemas import BacktestRequest, CalculationRequest, FinalAnswer
from src.data_providers.market_data import MarketDataError
from src.orchestration.backtest_pipeline import run_backtest_pipeline

router = APIRouter()


@router.post("/run", response_model=FinalAnswer)
def run(payload: BacktestRequest) -> FinalAnswer:
    """Run a single-ticker backtest with walk-forward, slippage sensitivity,
    and look-ahead detection."""
    request = CalculationRequest(raw_input=payload.model_dump_json())
    try:
        answer, _ = run_backtest_pipeline(request, payload)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {type(exc).__name__}",
        ) from exc
    return answer
