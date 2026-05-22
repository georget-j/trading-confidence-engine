"""Chat routes — NL-driven parsing that feeds the verified pipeline.

These endpoints are the *only* place the LLM runs. The LLM's output is the
structured request object; numerical answers still come exclusively from the
deterministic pipeline at /calc/options/price.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from src.core.schemas import (
    BacktestRequest,
    CalculationRequest,
    FinalAnswer,
    OptionsPricingRequest,
    PortfolioRequest,
    VaRRequest,
)
from src.llm.router import (
    LLMBacktestParse,
    LLMOptionsParse,
    LLMPortfolioParse,
    LLMUnavailable,
    LLMVaRParse,
    parse_backtest_nl,
    parse_options_nl,
    parse_portfolio_nl,
    parse_var_nl,
)
from src.orchestration.pipeline import run_pipeline

router = APIRouter()


class ChatParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class ChatParseResponse(BaseModel):
    """What the /chat/parse endpoint returns. Note the deliberate absence of
    any numerical pricing fields — those come only from /chat/price (or the
    structured /calc/options/price)."""

    model_config = ConfigDict(extra="forbid")

    structured: OptionsPricingRequest | None
    raw_parse: LLMOptionsParse
    ready_to_price: bool


class ChatPriceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_parse: LLMOptionsParse
    answer: FinalAnswer


@router.post("/parse", response_model=ChatParseResponse)
def chat_parse(req: ChatParseRequest) -> ChatParseResponse:
    """Convert NL into a structured OptionsPricingRequest (or explain what's missing).

    Returns 503 when no LLM is configured — the structured /calc endpoints
    keep working in that case.
    """
    try:
        structured, parse = parse_options_nl(req.text)
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatParseResponse(
        structured=structured,
        raw_parse=parse,
        ready_to_price=structured is not None,
    )


@router.post("/price", response_model=ChatPriceResponse)
def chat_price(req: ChatParseRequest) -> ChatPriceResponse:
    """Parse NL and run the full verification pipeline in one call.

    Refuses to price if the LLM couldn't extract a complete request — returns
    the raw parse so the UI can prompt the user for missing fields.
    """
    try:
        structured, parse = parse_options_nl(req.text)
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if structured is None:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Couldn't extract a complete pricing request.",
                "parse": parse.model_dump(mode="json"),
            },
        )

    calc_request = CalculationRequest(raw_input=req.text)
    answer, _audit = run_pipeline(calc_request, parsed_payload=structured)
    return ChatPriceResponse(raw_parse=parse, answer=answer)


# ---- VaR -------------------------------------------------------------------


class ChatVaRParseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    structured: VaRRequest | None
    raw_parse: LLMVaRParse
    ready_to_compute: bool


@router.post("/parse/var", response_model=ChatVaRParseResponse)
def chat_parse_var(req: ChatParseRequest) -> ChatVaRParseResponse:
    """Convert NL into a structured VaRRequest."""
    try:
        structured, parse = parse_var_nl(req.text)
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatVaRParseResponse(
        structured=structured,
        raw_parse=parse,
        ready_to_compute=structured is not None,
    )


# ---- Portfolio -------------------------------------------------------------


class ChatPortfolioParseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    structured: PortfolioRequest | None
    raw_parse: LLMPortfolioParse
    ready_to_optimise: bool


@router.post("/parse/portfolio", response_model=ChatPortfolioParseResponse)
def chat_parse_portfolio(req: ChatParseRequest) -> ChatPortfolioParseResponse:
    """Convert NL into a structured PortfolioRequest."""
    try:
        structured, parse = parse_portfolio_nl(req.text)
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatPortfolioParseResponse(
        structured=structured,
        raw_parse=parse,
        ready_to_optimise=structured is not None,
    )


# ---- Backtest --------------------------------------------------------------


class ChatBacktestParseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    structured: BacktestRequest | None
    raw_parse: LLMBacktestParse
    ready_to_run: bool


@router.post("/parse/backtest", response_model=ChatBacktestParseResponse)
def chat_parse_backtest(req: ChatParseRequest) -> ChatBacktestParseResponse:
    """Convert NL into a structured BacktestRequest."""
    try:
        structured, parse = parse_backtest_nl(req.text)
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatBacktestParseResponse(
        structured=structured,
        raw_parse=parse,
        ready_to_run=structured is not None,
    )
