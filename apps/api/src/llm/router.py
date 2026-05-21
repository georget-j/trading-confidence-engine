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
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.core.schemas import OptionsPricingRequest, OptionStyle, OptionType

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


def _call_llm(text: str, *, model: str) -> LLMOptionsParse:
    # Imported lazily so the module is importable without litellm at all
    # (useful for type-only environments).
    import litellm

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format=LLMOptionsParse,
            timeout=DEFAULT_TIMEOUT_S,
        )
    except Exception as exc:
        LOG.exception("LLM call failed: %s", exc)
        raise LLMUnavailable(f"LLM call failed: {type(exc).__name__}: {exc}") from exc

    content = _extract_content(response)
    try:
        return LLMOptionsParse.model_validate_json(content)
    except ValidationError as exc:
        LOG.warning("LLM returned invalid JSON / schema mismatch: %s", exc)
        # One retry: try parsing as a dict (some providers double-encode).
        try:
            return LLMOptionsParse.model_validate(json.loads(content))
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
