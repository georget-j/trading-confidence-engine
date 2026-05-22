"""LLM router — the only place an LLM is allowed to run.

Hard rules enforced by this module:

1. The LLM ONLY produces a structured `OptionsPricingRequest`. It never
   produces a price, a Greek, or a verification status. Those come from the
   deterministic calculators in `src/calculators/` and the verifier in
   `src/verification/`.
2. The structured output is parsed against the Pydantic schema. If the LLM
   returns anything that doesn't validate, we raise — never silently coerce.
3. If no API key is configured we raise `LLMUnavailable`. The /calc endpoints
   keep working without the LLM; only the /chat endpoints need it.

The provider/model is selected by env vars:
    LLM_MODEL=anthropic/claude-haiku-4-5-20251001  (default)
    ANTHROPIC_API_KEY or OPENAI_API_KEY (whichever matches the model)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Annotated, Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.core.schemas import (
    BacktestRequest,
    BacktestStrategy,
    OptionsPricingRequest,
    OptionStyle,
    OptionType,
    PortfolioObjective,
    PortfolioRequest,
    VaRRequest,
)

LOG = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-haiku-4-5-20251001")
DEFAULT_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "15"))


class LLMUnavailable(RuntimeError):  # noqa: N818 — public exception name kept for clarity
    """Raised when the LLM cannot be reached (no key, network, or invalid output)."""


# ---- Output schema -----------------------------------------------------------


class LLMOptionsParse(BaseModel):
    """What we *let* the LLM produce. Note what's NOT here:
    - no `price` field
    - no `greeks` field
    - no `verification_status`
    The LLM has no way to claim a number is correct.
    """

    model_config = ConfigDict(extra="forbid")

    spot: float | None = Field(None, description="Underlying spot price in dollars")
    strike: float | None = Field(None, description="Strike price in dollars")
    time_to_expiry_days: float | None = Field(
        None, ge=0, description="Days until expiry. Convert weeks/months/years as needed."
    )
    volatility_pct: float | None = Field(
        None,
        description="Annualised implied volatility as a percentage (e.g. 18 for 18%)",
    )
    risk_free_rate_pct: float | None = Field(
        None,
        description="Risk-free rate as a percentage. If user does not specify, leave null.",
    )
    dividend_yield_pct: float | None = Field(
        None,
        ge=0,
        description="Dividend yield as a percentage. Default 0 if not specified.",
    )
    option_type: OptionType | None = None
    style: OptionStyle | None = Field(None, description="european or american")
    parse_confidence: Annotated[float, Field(ge=0, le=1)] = Field(
        ...,
        description=(
            "Your confidence that the user supplied enough information to compute "
            "the option price. Set <0.5 if any of spot/strike/expiry/vol is missing."
        ),
    )
    parser_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Briefly note any assumptions you made or fields that the user did not "
            "supply. One short bullet per assumption."
        ),
    )


# ---- Public API --------------------------------------------------------------


def parse_options_nl(text: str, *, model: str | None = None) -> tuple[
    OptionsPricingRequest | None, LLMOptionsParse
]:
    """Parse a natural-language options-pricing request.

    Returns a tuple `(structured_request, raw_parse)`:
      - `structured_request` is None when required fields are missing or
        confidence is too low (the API will then return the parse object so the
        UI can prompt the user to fill the gaps).
      - `raw_parse` always carries the LLM's best-effort fields plus notes.

    Raises `LLMUnavailable` if no LLM is configured or reachable.
    """
    if not _api_key_present(model or DEFAULT_MODEL):
        raise LLMUnavailable(
            "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    parse = _call_llm(text, model=model or DEFAULT_MODEL)
    structured = _to_structured(parse)
    return structured, parse


# ---- Implementation details --------------------------------------------------


SYSTEM_PROMPT = """\
You are a parser for a high-confidence options-pricing engine. Your one job is \
to extract structured fields from a user's natural-language pricing request.

HARD RULES:
- Do NOT compute prices, Greeks, or any numbers. A verified deterministic \
calculator will do that downstream.
- Do NOT invent fields. If the user did not state spot/strike/expiry/vol, leave \
the corresponding field null and add a parser note.
- Convert time units to days. "1 month" -> 30, "6 weeks" -> 42, "0.5 years" -> 182.
- Volatility, rates, and dividend yields are expressed as percentages \
(e.g. "20% IV" -> 20).
- option_type must be "call" or "put". style defaults to "european" unless the \
user explicitly says "american".
- parse_confidence should reflect how complete the request is, NOT how confident \
you are in the eventual price."""


_T = TypeVar("_T", bound=BaseModel)


def _call_llm(text: str, *, model: str) -> LLMOptionsParse:
    """Backwards-compatible wrapper for the options parser."""
    return _structured_call(text, model=model, schema=LLMOptionsParse, system=SYSTEM_PROMPT)


def _structured_call(
    text: str,
    *,
    model: str,
    schema: type[_T],
    system: str,
) -> _T:
    """Call the LLM with a structured-output schema and return a validated model.

    Always raises `LLMUnavailable` on any failure (transport, content, schema).
    The schema MUST omit any pricing/numerical-result fields — the LLM may not
    propose answers, only inputs.
    """
    import litellm

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            response_format=schema,
            timeout=DEFAULT_TIMEOUT_S,
        )
    except Exception as exc:
        LOG.exception("LLM call failed: %s", exc)
        raise LLMUnavailable(f"LLM call failed: {type(exc).__name__}: {exc}") from exc

    content = _extract_content(response)
    try:
        return schema.model_validate_json(content)
    except ValidationError as exc:
        LOG.warning("LLM returned invalid JSON / schema mismatch: %s", exc)
        # One retry: try parsing as a dict (some providers double-encode).
        try:
            return schema.model_validate(json.loads(content))
        except Exception as inner:
            raise LLMUnavailable(
                f"LLM output did not match schema: {inner}"
            ) from inner


def _extract_content(response: Any) -> str:
    """Pull the assistant text out of litellm's normalised response shape."""
    try:
        return str(response["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMUnavailable(f"Unexpected LLM response shape: {exc}") from exc


def _to_structured(parse: LLMOptionsParse) -> OptionsPricingRequest | None:
    """Build an OptionsPricingRequest only if all required fields are present
    AND parse_confidence is high enough. Otherwise return None and let the
    caller surface the parse object's notes to the user.
    """
    required = (
        parse.spot,
        parse.strike,
        parse.time_to_expiry_days,
        parse.volatility_pct,
        parse.option_type,
    )
    if any(v is None for v in required) or parse.parse_confidence < 0.5:
        return None

    # mypy: narrowed by the check above
    assert parse.spot is not None
    assert parse.strike is not None
    assert parse.time_to_expiry_days is not None
    assert parse.volatility_pct is not None
    assert parse.option_type is not None

    return OptionsPricingRequest(
        spot=parse.spot,
        strike=parse.strike,
        time_to_expiry_years=parse.time_to_expiry_days / 365.0,
        volatility=parse.volatility_pct / 100.0,
        risk_free_rate=(parse.risk_free_rate_pct or 0.0) / 100.0,
        dividend_yield=(parse.dividend_yield_pct or 0.0) / 100.0,
        option_type=parse.option_type,
        style=parse.style or OptionStyle.EUROPEAN,
    )


def _api_key_present(model: str) -> bool:
    """Cheap pre-flight: do we have a key matching the configured model?"""
    if model.startswith("anthropic/") or model.startswith("claude"):
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    if model.startswith("openai/") or model.startswith("gpt"):
        return bool(os.getenv("OPENAI_API_KEY"))
    # Unknown prefix: best effort — let the call fail downstream.
    return True


# ============================================================================
# VaR parser
# ============================================================================


class LLMVaRParse(BaseModel):
    """Structured VaR parse. No numerical results (var_loss / cvar_loss) —
    those come from the deterministic /calc/risk/var pipeline."""

    model_config = ConfigDict(extra="forbid")

    ticker: str | None = Field(None, description="Ticker symbol, e.g. SPY, AAPL, NVDA.")
    lookback_days: int | None = Field(
        None,
        ge=30,
        le=2520,
        description=(
            "How many trading days of history to use. Convert weeks/months/years. "
            "1 year ≈ 252, 2 years ≈ 504. Leave null if unspecified."
        ),
    )
    portfolio_value: float | None = Field(
        None, gt=0, description="Dollar size of the portfolio. Leave null if unspecified."
    )
    confidence_level: float | None = Field(
        None,
        gt=0.5,
        lt=1.0,
        description=(
            "Confidence as a decimal, e.g. 0.95 for 95%, 0.99 for 99%. "
            "Leave null if unspecified."
        ),
    )
    horizon_days: int | None = Field(
        None,
        ge=1,
        le=252,
        description="Days into the future the loss measures. Default 1 day if unstated.",
    )
    parse_confidence: Annotated[float, Field(ge=0, le=1)] = Field(
        ...,
        description=(
            "Your confidence that the user specified at least a ticker. "
            "Set <0.5 if the ticker is ambiguous or missing."
        ),
    )
    parser_notes: list[str] = Field(default_factory=list)


VAR_SYSTEM_PROMPT = """\
You are a parser for a high-confidence Value-at-Risk engine. Your one job is \
to extract structured fields from a user's natural-language VaR request.

HARD RULES:
- Do NOT compute VaR, CVaR, or any losses. A verified deterministic calculator \
will do that downstream.
- Do NOT invent fields. If the user did not state portfolio value, leave it null.
- Ticker MUST be a real exchange symbol (SPY, AAPL, NVDA, ^GSPC for the S&P 500). \
If the user says "tech stocks" or "the market", set ticker null and add a note.
- confidence_level is a decimal: "95%" -> 0.95, "99%" -> 0.99.
- Convert lookback units to trading days: "1 year" -> 252, "6 months" -> 126, \
"2 years" -> 504.
- parse_confidence reflects request completeness, NOT confidence in the result."""


def parse_var_nl(
    text: str, *, model: str | None = None
) -> tuple[VaRRequest | None, LLMVaRParse]:
    """Parse an NL VaR request. Same contract as `parse_options_nl`."""
    if not _api_key_present(model or DEFAULT_MODEL):
        raise LLMUnavailable(
            "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    parse = _structured_call(
        text,
        model=model or DEFAULT_MODEL,
        schema=LLMVaRParse,
        system=VAR_SYSTEM_PROMPT,
    )
    structured = _var_to_structured(parse)
    return structured, parse


def _var_to_structured(parse: LLMVaRParse) -> VaRRequest | None:
    if parse.ticker is None or parse.parse_confidence < 0.5:
        return None
    kwargs: dict[str, Any] = {"ticker": parse.ticker}
    if parse.lookback_days is not None:
        kwargs["lookback_days"] = parse.lookback_days
    if parse.portfolio_value is not None:
        kwargs["portfolio_value"] = parse.portfolio_value
    if parse.confidence_level is not None:
        kwargs["confidence_level"] = parse.confidence_level
    if parse.horizon_days is not None:
        kwargs["horizon_days"] = parse.horizon_days
    try:
        return VaRRequest(**kwargs)
    except ValidationError as exc:
        LOG.warning("LLM VaR parse produced invalid request: %s", exc)
        return None


# ============================================================================
# Portfolio parser
# ============================================================================


class LLMPortfolioParse(BaseModel):
    """Structured portfolio optimisation parse."""

    model_config = ConfigDict(extra="forbid")

    tickers: list[str] | None = Field(
        None,
        description=(
            "2-20 ticker symbols. Real exchange tickers only — do not invent "
            "from sector descriptions."
        ),
    )
    lookback_days: int | None = Field(None, ge=60, le=2520)
    objective: PortfolioObjective | None = Field(
        None,
        description=(
            '"mean_variance", "max_sharpe", or "risk_parity". Default to '
            "mean_variance if unspecified."
        ),
    )
    risk_aversion: float | None = Field(
        None,
        gt=0,
        le=100,
        description="Mean-variance only. Typical retail values 2-5.",
    )
    max_weight: float | None = Field(
        None,
        gt=0,
        le=1.0,
        description="Per-asset cap, e.g. 0.40 for 40%. Default 0.40 if unspecified.",
    )
    parse_confidence: Annotated[float, Field(ge=0, le=1)] = Field(...)
    parser_notes: list[str] = Field(default_factory=list)


PORTFOLIO_SYSTEM_PROMPT = """\
You are a parser for a portfolio-optimisation engine. Your job is to extract \
structured fields from a user's NL request.

HARD RULES:
- Do NOT compute weights or any numeric output. A deterministic optimiser does that.
- tickers MUST be real exchange symbols (2-20). If the user gives sector \
descriptions only ("tech stocks", "FAANG"), set tickers null and add a note.
- objective is "mean_variance" or "max_sharpe". Default mean_variance.
- max_weight is a decimal (40% -> 0.40).
- parse_confidence reflects request completeness."""


def parse_portfolio_nl(
    text: str, *, model: str | None = None
) -> tuple[PortfolioRequest | None, LLMPortfolioParse]:
    if not _api_key_present(model or DEFAULT_MODEL):
        raise LLMUnavailable(
            "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    parse = _structured_call(
        text,
        model=model or DEFAULT_MODEL,
        schema=LLMPortfolioParse,
        system=PORTFOLIO_SYSTEM_PROMPT,
    )
    structured = _portfolio_to_structured(parse)
    return structured, parse


def _portfolio_to_structured(parse: LLMPortfolioParse) -> PortfolioRequest | None:
    if (
        parse.tickers is None
        or len(parse.tickers) < 2
        or parse.parse_confidence < 0.5
    ):
        return None
    kwargs: dict[str, Any] = {"tickers": parse.tickers}
    if parse.lookback_days is not None:
        kwargs["lookback_days"] = parse.lookback_days
    if parse.objective is not None:
        kwargs["objective"] = parse.objective
    if parse.risk_aversion is not None:
        kwargs["risk_aversion"] = parse.risk_aversion
    if parse.max_weight is not None:
        kwargs["max_weight"] = parse.max_weight
    try:
        return PortfolioRequest(**kwargs)
    except ValidationError as exc:
        LOG.warning("LLM portfolio parse produced invalid request: %s", exc)
        return None


# ============================================================================
# Backtest parser
# ============================================================================


class LLMBacktestParse(BaseModel):
    """Structured backtest parse."""

    model_config = ConfigDict(extra="forbid")

    ticker: str | None = Field(None, description="Single ticker, e.g. SPY, AAPL.")
    lookback_days: int | None = Field(None, ge=120, le=2520)
    strategy: BacktestStrategy | None = Field(
        None,
        description='"buy_and_hold", "ma_crossover", or "momentum". Default ma_crossover.',
    )
    initial_capital: float | None = Field(None, gt=0)
    slippage_bps: float | None = Field(
        None,
        ge=0,
        le=200,
        description="Per-trade slippage in basis points. 5 = 0.05% per trade.",
    )
    parse_confidence: Annotated[float, Field(ge=0, le=1)] = Field(...)
    parser_notes: list[str] = Field(default_factory=list)


BACKTEST_SYSTEM_PROMPT = """\
You are a parser for a backtesting engine. Your job is to extract structured \
fields from a user's NL request.

HARD RULES:
- Do NOT compute returns, Sharpe, or any metrics.
- ticker MUST be a real single exchange symbol. If the user says "tech stocks" \
or gives multiple tickers, set ticker null and add a note (multi-ticker \
backtest isn't supported yet).
- strategy is "buy_and_hold", "ma_crossover", or "momentum". Default ma_crossover \
unless the user clearly says "buy and hold" or "momentum".
- slippage_bps default 5 if unstated (5 bps = 0.05% per trade).
- Convert lookback units to trading days."""


def parse_backtest_nl(
    text: str, *, model: str | None = None
) -> tuple[BacktestRequest | None, LLMBacktestParse]:
    if not _api_key_present(model or DEFAULT_MODEL):
        raise LLMUnavailable(
            "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    parse = _structured_call(
        text,
        model=model or DEFAULT_MODEL,
        schema=LLMBacktestParse,
        system=BACKTEST_SYSTEM_PROMPT,
    )
    structured = _backtest_to_structured(parse)
    return structured, parse


def _backtest_to_structured(parse: LLMBacktestParse) -> BacktestRequest | None:
    if parse.ticker is None or parse.parse_confidence < 0.5:
        return None
    kwargs: dict[str, Any] = {"ticker": parse.ticker}
    if parse.lookback_days is not None:
        kwargs["lookback_days"] = parse.lookback_days
    if parse.strategy is not None:
        kwargs["strategy"] = parse.strategy
    if parse.initial_capital is not None:
        kwargs["initial_capital"] = parse.initial_capital
    if parse.slippage_bps is not None:
        kwargs["slippage_bps"] = parse.slippage_bps
    try:
        return BacktestRequest(**kwargs)
    except ValidationError as exc:
        LOG.warning("LLM backtest parse produced invalid request: %s", exc)
        return None
