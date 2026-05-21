"""Options-pricing parser.

V0/V1: explicit structured input only — the API takes typed JSON, so the
"parser" just lifts it into a ParsedRequest. NL parsing arrives in V2 when
the LLM layer goes in.
"""

from __future__ import annotations

from src.core.schemas import (
    CalcFamily,
    CalculationRequest,
    OptionsPricingRequest,
    ParsedRequest,
)


class ParserError(ValueError):
    """Raised when the raw input cannot be lifted into a structured request."""


def parse_options_request(request: CalculationRequest) -> ParsedRequest:
    """Lift a raw request into a typed ParsedRequest.

    V0/V1 behaviour: refuses to guess from natural language. The caller must
    use the structured API endpoint, which feeds a typed payload directly into
    `run_pipeline(..., parsed_payload=...)`. This guarantees we never silently
    fabricate parameters.
    """
    raise ParserError(
        "Natural-language parsing is not yet implemented. Use the structured "
        "/calc/options/price endpoint, or supply parsed_payload explicitly."
    )


def lift_payload(
    request: CalculationRequest,
    payload: OptionsPricingRequest,
) -> ParsedRequest:
    """Wrap a pre-validated payload in a ParsedRequest envelope."""
    return ParsedRequest(
        request_id=request.request_id,
        family=CalcFamily.OPTIONS_PRICING,
        payload=payload,
    )
