"""Portfolio-optimization routes (V6)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.core.schemas import CalculationRequest, FinalAnswer, PortfolioRequest
from src.data_providers.market_data import MarketDataError
from src.orchestration.portfolio_pipeline import run_portfolio_pipeline

router = APIRouter()


@router.post("/optimize", response_model=FinalAnswer)
def optimize_portfolio(payload: PortfolioRequest) -> FinalAnswer:
    """Solve a long-only mean-variance or max-Sharpe portfolio with
    cross-solver and sensitivity verification.

    The response carries a verification_status that distinguishes a stable
    well-conditioned optimum from a fragile one that swings under small
    input noise.
    """
    request = CalculationRequest(raw_input=payload.model_dump_json())
    try:
        answer, _ = run_portfolio_pipeline(request, payload)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Portfolio optimization failed: {type(exc).__name__}",
        ) from exc
    return answer
