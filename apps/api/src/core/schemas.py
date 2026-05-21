"""Pydantic schemas — the typed contract for every pipeline stage.

Every stage of the pipeline consumes and emits one of these objects.
Final numbers in `FinalAnswer.value` MUST originate from a `CalculatorResult`,
not from an LLM. The schema is the enforcement point.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class CalcFamily(StrEnum):
    OPTIONS_PRICING = "options_pricing"
    RISK_METRICS = "risk_metrics"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    BACKTEST = "backtest"
    UNKNOWN = "unknown"


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


class OptionStyle(StrEnum):
    EUROPEAN = "european"
    AMERICAN = "american"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    NOT_VERIFIED = "not_verified"


class _BaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class CalculationRequest(_BaseModel):
    """Raw user-facing request — what the user typed or filled in."""

    request_id: UUID = Field(default_factory=uuid4)
    raw_input: str
    family_hint: CalcFamily | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---- Per-family parsed-request payloads ------------------------------------


class OptionsPricingRequest(_BaseModel):
    """Structured options-pricing request after parsing."""

    spot: Annotated[float, Field(gt=0, description="Underlying spot price")]
    strike: Annotated[float, Field(gt=0, description="Strike price")]
    time_to_expiry_years: Annotated[
        float, Field(gt=0, le=10, description="Time to expiry in years")
    ]
    volatility: Annotated[
        float, Field(gt=0, le=5.0, description="Annualised volatility (e.g. 0.20 = 20%)")
    ]
    risk_free_rate: Annotated[
        float, Field(ge=-0.1, le=1.0, description="Continuously-compounded risk-free rate")
    ]
    dividend_yield: Annotated[
        float, Field(ge=0, le=1.0, description="Continuous dividend yield")
    ] = 0.0
    option_type: OptionType
    style: OptionStyle = OptionStyle.EUROPEAN


# Discriminated union — extend with risk/portfolio/backtest payloads in later versions.
ParsedPayload = Annotated[OptionsPricingRequest, Field(discriminator=None)]


class ParsedRequest(_BaseModel):
    """Output of the parser — structured, validated, family-aware."""

    request_id: UUID
    family: CalcFamily
    payload: OptionsPricingRequest
    parse_confidence: Annotated[float, Field(ge=0, le=1)] = 1.0
    parser_notes: list[str] = Field(default_factory=list)


# ---- Calculator outputs ----------------------------------------------------


class GreeksPayload(_BaseModel):
    """Standard first/second-order Greeks. Units are per-unit-of-underlying for delta/gamma,
    per-1.00-vol (i.e. per 100% absolute) for vega, per-year for theta, per-1.00-rate for rho.
    """

    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


class OptionsPriceResult(_BaseModel):
    kind: Literal["options_price"] = "options_price"
    price: float
    greeks: GreeksPayload | None = None


# ---- Risk / VaR --------------------------------------------------------------


class VaRRequest(_BaseModel):
    """Inputs for a Value-at-Risk calculation.

    Either `returns` OR (`ticker` + `lookback_days`) must be supplied. VaR is
    reported as a POSITIVE loss number (e.g. var_95 = 230 means "5% chance of
    losing more than $230 over the stated horizon").
    """

    ticker: str | None = Field(
        None, description="Equity ticker. If set, daily returns are fetched server-side."
    )
    lookback_days: Annotated[int, Field(ge=30, le=2520)] = 504  # ~2 years
    returns: list[float] | None = Field(
        None,
        description=(
            "Daily simple returns (decimal, e.g. 0.012 for +1.2%). If set, "
            "overrides any ticker fetch. Must contain at least 30 observations."
        ),
    )
    portfolio_value: Annotated[float, Field(gt=0)] = 10_000.0
    confidence_level: Annotated[float, Field(gt=0.5, lt=1.0)] = 0.95
    horizon_days: Annotated[int, Field(ge=1, le=252)] = 1
    monte_carlo_paths: Annotated[int, Field(ge=1_000, le=1_000_000)] = 100_000


class HistogramBin(_BaseModel):
    """One bucket of a returns histogram. All edges in decimal return space
    (e.g. -0.02 = -2% daily return)."""

    bin_min: float
    bin_max: float
    count: int


class VaRPayload(_BaseModel):
    """Result from one VaR method."""

    kind: Literal["var"] = "var"
    var_loss: float = Field(description="Value at Risk as a positive loss in dollars")
    cvar_loss: float = Field(description="Expected Shortfall as a positive loss in dollars")
    mean_return: float
    volatility: float
    n_observations: int
    # Optional retail-friendly viz extras. Populated by the historical method
    # (the no-assumption baseline). Other methods leave these null.
    histogram_bins: list[HistogramBin] | None = None
    var_return_quantile: float | None = Field(
        None,
        description="Daily return at the VaR threshold (negative). Used for chart shading.",
    )
    cvar_return_quantile: float | None = Field(
        None,
        description="Mean daily return in the tail beyond VaR. Used for chart shading.",
    )


# ---- Portfolio optimization -------------------------------------------------


class PortfolioObjective(StrEnum):
    MEAN_VARIANCE = "mean_variance"
    MAX_SHARPE = "max_sharpe"


class PortfolioRequest(_BaseModel):
    """Inputs for a long-only portfolio optimization.

    Returns are fetched from the configured data provider for each ticker;
    the in-sample mean and covariance are estimated from those returns.
    """

    tickers: list[str] = Field(min_length=2, max_length=20)
    lookback_days: Annotated[int, Field(ge=60, le=2520)] = 504
    risk_free_rate: Annotated[float, Field(ge=-0.05, le=0.25)] = 0.04
    objective: PortfolioObjective = PortfolioObjective.MEAN_VARIANCE
    risk_aversion: Annotated[float, Field(gt=0, le=100)] = 2.0


class AssetWeight(_BaseModel):
    ticker: str
    weight: float
    risk_contribution: float = Field(
        description=(
            "Share of total portfolio variance attributable to this asset. "
            "Sums to 1 across the portfolio."
        ),
    )


class PortfolioPayload(_BaseModel):
    kind: Literal["portfolio"] = "portfolio"
    objective: PortfolioObjective
    weights: list[AssetWeight]
    expected_return_annualised: float
    volatility_annualised: float
    sharpe_ratio: float
    solver_name: str
    iterations: int | None = None
    # Sensitivity: how much weights move under small input perturbations.
    # 0 = perfectly stable, 1 = catastrophically unstable.
    instability_score: float | None = Field(
        None, ge=0, le=1, description="Fraction of weights that shifted >1% under perturbed inputs."
    )


# Discriminated union over all calculator payload types.
CalcResultPayload = Annotated[
    OptionsPriceResult | VaRPayload | PortfolioPayload,
    Field(discriminator="kind"),
]


class CalculatorResult(_BaseModel):
    """Output of one independent calculation method (e.g. py_vollib closed-form)."""

    calculator_id: str
    method_name: str
    payload: CalcResultPayload
    duration_ms: float
    succeeded: bool = True
    error: str | None = None


# ---- Verification ----------------------------------------------------------


class CrossMethodCheck(_BaseModel):
    methods_compared: list[str]
    max_absolute_delta: float
    max_relative_delta: float
    tolerance: float
    passed: bool


class InvariantCheck(_BaseModel):
    name: str
    description: str
    passed: bool
    detail: str | None = None


class VerificationResult(_BaseModel):
    cross_method: CrossMethodCheck | None = None
    invariants: list[InvariantCheck] = Field(default_factory=list)
    method_agreement_score: Annotated[float, Field(ge=0, le=1)]
    bounds_check_score: Annotated[float, Field(ge=0, le=1)]
    input_quality_score: Annotated[float, Field(ge=0, le=1)] = 1.0
    numerical_stability_score: Annotated[float, Field(ge=0, le=1)] = 1.0
    overall_status: VerificationStatus


# ---- Final answer ----------------------------------------------------------


class FinalAnswer(_BaseModel):
    """What gets returned to the API caller / UI."""

    request_id: UUID
    family: CalcFamily
    verification_status: VerificationStatus
    primary_result: CalcResultPayload
    calculator_results: list[CalculatorResult]
    verification: VerificationResult
    explanation: str
    limitations: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---- Audit log -------------------------------------------------------------


class AuditEntry(_BaseModel):
    """One row in the audit log — records the output of one pipeline stage."""

    stage: Literal[
        "request",
        "parse",
        "calculate",
        "verify",
        "explain",
        "respond",
    ]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]


class AuditLog(BaseModel):
    """Mutable on purpose — the pipeline runner appends entries as stages complete."""

    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    entries: list[AuditEntry] = Field(default_factory=list)
