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

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    kind: Literal["options_request"] = "options_request"
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


# ---- Multi-leg options strategies ------------------------------------------


class StrategyLeg(_BaseModel):
    """One leg of a multi-leg options strategy.

    `quantity` is signed: +N = long N contracts, -N = short N contracts.
    `time_to_expiry_years` and `volatility` are per-leg so calendars and
    vertical spreads with mixed IV can be expressed.
    """

    option_type: OptionType
    strike: Annotated[float, Field(gt=0)]
    quantity: Annotated[int, Field(ge=-100, le=100)]
    time_to_expiry_years: Annotated[float, Field(gt=0, le=10)]
    volatility: Annotated[float, Field(gt=0, le=5.0)]

    @model_validator(mode="after")
    def _quantity_nonzero(self) -> StrategyLeg:
        if self.quantity == 0:
            raise ValueError("Leg quantity must be non-zero.")
        return self


class OptionsStrategyRequest(_BaseModel):
    """Multi-leg European-style options strategy.

    Underlying (spot, rate, dividend) is shared across legs. Strike, type,
    quantity, expiry, and IV are per leg. Single-leg strategies should use
    the existing `/calc/options/price` endpoint — `min_length=2` enforces
    that here.
    """

    kind: Literal["options_strategy_request"] = "options_strategy_request"
    spot: Annotated[float, Field(gt=0)]
    risk_free_rate: Annotated[float, Field(ge=-0.1, le=1.0)]
    dividend_yield: Annotated[float, Field(ge=0, le=1.0)] = 0.0
    style: OptionStyle = OptionStyle.EUROPEAN
    legs: list[StrategyLeg] = Field(min_length=2, max_length=4)


class StrategyLegResult(_BaseModel):
    """Priced leg — echoes the leg inputs plus the computed price and Greeks.

    `price` is per-contract, positive. The sign of `quantity` determines whether
    a leg contributes positively (long) or negatively (short) to net premium.
    """

    option_type: OptionType
    strike: float
    quantity: int
    time_to_expiry_years: float
    volatility: float
    price: float
    greeks: GreeksPayload | None = None


class OptionsStrategyPayload(_BaseModel):
    """Aggregate result of pricing a strategy.

    `net_premium = sum(quantity * leg.price)` — positive for net debit
    strategies (e.g. long call), negative for net credit (e.g. short put).
    `net_greeks` is the quantity-weighted sum across all legs.
    """

    kind: Literal["options_strategy"] = "options_strategy"
    legs: list[StrategyLegResult]
    net_premium: float
    net_greeks: GreeksPayload


# ---- Risk / VaR --------------------------------------------------------------


class VaRRequest(_BaseModel):
    """Inputs for a Value-at-Risk calculation.

    Either `returns` OR (`ticker` + `lookback_days`) must be supplied. VaR is
    reported as a POSITIVE loss number (e.g. var_95 = 230 means "5% chance of
    losing more than $230 over the stated horizon").
    """

    kind: Literal["var_request"] = "var_request"
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
    # C2: downside-aware return/risk ratios derived from the same returns
    # series. Populated by the historical method; other methods leave null.
    sortino_ratio: float | None = Field(
        None,
        description=(
            "Annualised excess return / downside deviation. Like Sharpe but "
            "penalises only negative deviations from the mean."
        ),
    )
    calmar_ratio: float | None = Field(
        None,
        description=(
            "Annualised return / max drawdown of the cumulative return series. "
            "High Calmar = returns dwarf the worst peak-to-trough loss."
        ),
    )
    max_drawdown: float | None = Field(
        None,
        ge=0,
        description=(
            "Worst peak-to-trough decline of the implied cumulative-return "
            "series, as a positive fraction (e.g. 0.18 = -18% drawdown)."
        ),
    )


# ---- Portfolio optimization -------------------------------------------------


class PortfolioObjective(StrEnum):
    MEAN_VARIANCE = "mean_variance"
    MAX_SHARPE = "max_sharpe"
    RISK_PARITY = "risk_parity"
    MIN_VARIANCE = "min_variance"
    INVERSE_VOL = "inverse_vol"


class PortfolioRequest(_BaseModel):
    """Inputs for a long-only portfolio optimization.

    Returns are fetched from the configured data provider for each ticker;
    the in-sample mean and covariance are estimated from those returns.

    Defaults bias the optimizer towards diversified, robust portfolios:
    `max_weight=0.40` prevents 100%-in-one-asset over-fitting, and
    `shrink_covariance=True` applies Ledoit-Wolf shrinkage which is widely
    cited as the single most effective fix for mean-variance fragility.
    """

    kind: Literal["portfolio_request"] = "portfolio_request"
    tickers: list[str] = Field(min_length=2, max_length=20)
    lookback_days: Annotated[int, Field(ge=60, le=2520)] = 504
    risk_free_rate: Annotated[float, Field(ge=-0.05, le=0.25)] = 0.04
    objective: PortfolioObjective = PortfolioObjective.MEAN_VARIANCE
    risk_aversion: Annotated[float, Field(gt=0, le=100)] = 2.0
    max_weight: Annotated[float, Field(gt=0, le=1.0)] = 0.40
    min_weight: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    shrink_covariance: bool = True

    @model_validator(mode="before")
    @classmethod
    def _auto_relax_max_weight(cls, data: object) -> object:
        """If the chosen max_weight is too tight to ever sum to 1, relax it
        to the minimum feasible value. Keeps the small-portfolio UX clean —
        a user with two tickers shouldn't need to know about the 1/n floor.
        """
        if not isinstance(data, dict):
            return data
        tickers = data.get("tickers")
        if not isinstance(tickers, list) or len(tickers) < 2:
            return data
        max_w = data.get("max_weight", 0.40)
        if not isinstance(max_w, int | float):
            return data
        needed = 1.0 / len(tickers)
        if max_w < needed:
            data["max_weight"] = min(1.0, needed + 1e-6)
        return data

    @model_validator(mode="after")
    def _check_weight_bounds_feasible(self) -> PortfolioRequest:
        n = len(self.tickers)
        if self.min_weight * n > 1.0 + 1e-9:
            raise ValueError(
                f"min_weight={self.min_weight} too large for {n} tickers: "
                f"forces sum > 1 (min possible sum = {self.min_weight * n:.2f})"
            )
        if self.min_weight >= self.max_weight:
            raise ValueError(
                f"min_weight ({self.min_weight}) must be < max_weight ({self.max_weight})"
            )
        return self


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


# ---- Backtesting -----------------------------------------------------------


class BacktestStrategy(StrEnum):
    BUY_AND_HOLD = "buy_and_hold"
    MA_CROSSOVER = "ma_crossover"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BOLLINGER = "bollinger"


class BacktestRequest(_BaseModel):
    """Inputs for a single-ticker backtest with sensitivity verification."""

    kind: Literal["backtest_request"] = "backtest_request"
    ticker: str
    lookback_days: Annotated[int, Field(ge=120, le=2520)] = 504
    strategy: BacktestStrategy = BacktestStrategy.MA_CROSSOVER
    initial_capital: Annotated[float, Field(gt=0)] = 10_000.0
    slippage_bps: Annotated[float, Field(ge=0, le=200)] = 5.0
    # Strategy-specific knobs:
    ma_fast: Annotated[int, Field(ge=2, le=200)] = 20
    ma_slow: Annotated[int, Field(ge=3, le=400)] = 50
    momentum_lookback: Annotated[int, Field(ge=5, le=252)] = 60
    # Mean-reversion: long when z-score < -entry; flat when |z| < exit.
    mean_rev_lookback: Annotated[int, Field(ge=5, le=252)] = 20
    mean_rev_entry_z: Annotated[float, Field(gt=0, le=5)] = 1.5
    # Bollinger: long when price crosses below (mean - mult·σ); exit at mean.
    bollinger_lookback: Annotated[int, Field(ge=5, le=252)] = 20
    bollinger_mult: Annotated[float, Field(gt=0, le=5)] = 2.0


class EquityPoint(_BaseModel):
    """One row of the equity curve."""

    day_index: int
    equity: float
    position: float = Field(
        description="Position size at this point (1 = fully invested, 0 = cash)"
    )


class BacktestMetrics(_BaseModel):
    """Headline performance metrics. All annualised values assume 252 trading days."""

    total_return: float
    annualised_return: float
    annualised_volatility: float
    sharpe_ratio: float
    max_drawdown: float = Field(description="Largest peak-to-trough decline (positive number).")
    calmar_ratio: float = Field(description="Annualised return / max drawdown.")
    win_rate: float = Field(description="Fraction of trading days with positive PnL.")
    n_trades: int


class SlippageSensitivity(_BaseModel):
    """How total return varies with slippage assumptions."""

    bps: list[float]
    total_return: list[float]


class BacktestPayload(_BaseModel):
    kind: Literal["backtest"] = "backtest"
    strategy: BacktestStrategy
    ticker: str
    metrics: BacktestMetrics
    benchmark_metrics: BacktestMetrics | None = Field(
        None,
        description="Buy-and-hold comparison on the same data, when the primary strategy isn't BH.",
    )
    equity_curve: list[EquityPoint]
    slippage_sensitivity: SlippageSensitivity
    walk_forward_reproducible: bool = Field(
        description="True iff running the backtest twice produces bit-identical equity curves."
    )
    lookahead_clean: bool = Field(
        description="True iff the look-ahead detector found no future-leaking patterns."
    )


# Discriminated union over every parsed-request payload type. Each member
# carries a `kind` Literal that disambiguates without callers needing to send
# it (the default fills in when JSON omits the tag).
ParsedPayload = Annotated[
    OptionsPricingRequest
    | OptionsStrategyRequest
    | VaRRequest
    | PortfolioRequest
    | BacktestRequest,
    Field(discriminator="kind"),
]


class ParsedRequest(_BaseModel):
    """Output of the parser — structured, validated, family-aware."""

    request_id: UUID
    family: CalcFamily
    payload: ParsedPayload
    parse_confidence: Annotated[float, Field(ge=0, le=1)] = 1.0
    parser_notes: list[str] = Field(default_factory=list)


# Discriminated union over all calculator payload types.
CalcResultPayload = Annotated[
    OptionsPriceResult
    | OptionsStrategyPayload
    | VaRPayload
    | PortfolioPayload
    | BacktestPayload,
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
