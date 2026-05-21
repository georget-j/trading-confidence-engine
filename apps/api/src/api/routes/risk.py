"""Risk metrics routes (V5)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.core.schemas import CalculationRequest, FinalAnswer, VaRRequest
from src.data_providers.market_data import MarketDataError
from src.orchestration.var_pipeline import run_var_pipeline

router = APIRouter()


@router.post("/var", response_model=FinalAnswer)
def value_at_risk(payload: VaRRequest) -> FinalAnswer:
    """Compute VaR/CVaR with three independent methods cross-verified.

    Supply either `returns` (a list of daily simple returns) or `ticker` (and
    optionally `lookback_days`) — at least one is required.
    """
    if payload.returns is None and payload.ticker is None:
        raise HTTPException(
            status_code=422,
            detail="Provide either `returns` or `ticker`.",
        )

    request = CalculationRequest(raw_input=payload.model_dump_json())
    try:
        answer, _audit = run_var_pipeline(request, payload)
    except MarketDataError as exc:
        # 502 because the failure is in the upstream data provider, not our logic.
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"VaR calculation failed: {type(exc).__name__}",
        ) from exc

    return answer
