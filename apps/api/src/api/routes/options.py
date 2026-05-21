"""Options-pricing routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.core.schemas import (
    CalculationRequest,
    FinalAnswer,
    OptionsPricingRequest,
)
from src.orchestration.pipeline import run_pipeline

router = APIRouter()


@router.post("/price", response_model=FinalAnswer)
def price(payload: OptionsPricingRequest) -> FinalAnswer:
    """Price a European option and return a verified result.

    The response carries `verification_status`. Clients SHOULD NOT treat
    `partially_verified` or `not_verified` as final answers — display them with
    the appropriate warning.
    """
    try:
        request = CalculationRequest(raw_input=payload.model_dump_json())
        answer, _audit = run_pipeline(request, parsed_payload=payload)
        return answer
    except Exception as exc:  # noqa: BLE001
        # Any uncaught exception is wrapped as 500 with a safe message. The
        # exception details stay in logs; we don't leak internals to clients.
        raise HTTPException(
            status_code=500,
            detail=f"Calculation failed: {type(exc).__name__}",
        ) from exc
