"""Phase 7 trader-pivot schemas — imported portfolios, sector breakdowns,
analytics payloads.

Kept in a separate module from ``schemas.py`` so the calculation-engine
contract stays focused. These types describe the input + output of the
Trade Ideas / My Portfolio / Hedge Finder / Compare workflows; they don't
flow through the verification pipeline directly (they orchestrate it).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class _BaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


# ---- Imported portfolio -----------------------------------------------------


class Holding(_BaseModel):
    """One position in an imported portfolio."""

    ticker: str = Field(min_length=1, max_length=20)
    shares: Annotated[float, Field(gt=0)]
    cost_basis: float | None = Field(
        default=None,
        description="Per-share cost basis in the holding's native currency.",
    )
    currency: str | None = Field(
        default=None,
        max_length=10,
        description="ISO currency code; None when the import didn't supply one.",
    )


class ImportedPortfolio(_BaseModel):
    """Result of parsing a Trading 212 / generic CSV (or paste)."""

    holdings: list[Holding] = Field(min_length=1, max_length=200)
    source: str = Field(
        description="Where the import came from: 'trading_212' | 'generic_csv' | 'paste'",
    )
    rows_seen: int = Field(
        description="Total rows read from the source before de-duplication.",
    )


# ---- Analysis payloads ------------------------------------------------------


class PricedHolding(_BaseModel):
    """A Holding enriched with live spot + value + sector."""

    ticker: str
    shares: float
    cost_basis: float | None
    currency: str | None
    spot: float
    value_usd: float
    weight: float = Field(
        ge=0, le=1, description="Fraction of total portfolio value."
    )
    sector: str | None
    industry: str | None
    pnl_usd: float | None = Field(
        default=None,
        description="Unrealised P/L vs cost_basis (None when cost_basis unknown).",
    )


class SectorExposure(_BaseModel):
    sector: str
    value_usd: float
    weight: float


class ConcentrationAlert(_BaseModel):
    """A specific concentration risk worth surfacing to the user."""

    kind: str  # "single_position" | "single_sector"
    label: str  # e.g. "NVDA" or "Technology"
    weight: float
    threshold: float
    message: str


class CorrelationMatrix(_BaseModel):
    """Symmetric square correlation matrix over the holdings universe."""

    tickers: list[str]
    matrix: list[list[float]] = Field(
        description="Row/column order matches `tickers`. Diagonal is 1.0.",
    )


class PortfolioAnalysis(_BaseModel):
    """Headline analytics for an imported portfolio."""

    total_value_usd: float
    holdings: list[PricedHolding]
    sector_exposure: list[SectorExposure]
    concentration_alerts: list[ConcentrationAlert] = Field(default_factory=list)
    portfolio_volatility_annualised: float | None = Field(
        default=None,
        description=(
            "Annualised stdev of portfolio daily returns over the lookback. "
            "None when not enough data was available."
        ),
    )
    correlation_matrix: CorrelationMatrix | None = None
    lookback_days: int
    limitations: list[str] = Field(default_factory=list)


# ---- Request envelopes ------------------------------------------------------


class PortfolioImportRequest(_BaseModel):
    """Inputs for /api/portfolio/import.

    Exactly one of ``csv_text`` or ``holdings`` should be provided. When
    ``csv_text`` is set, ``source`` chooses the parser.
    """

    csv_text: str | None = Field(default=None, description="Raw CSV body.")
    source: str = Field(
        default="trading_212",
        description="'trading_212' | 'generic_csv' | 'paste'",
    )
    holdings: list[Holding] | None = Field(
        default=None,
        description="Already-structured holdings (used for the paste flow).",
    )


class PortfolioAnalyseRequest(_BaseModel):
    holdings: list[Holding] = Field(min_length=1, max_length=200)
    lookback_days: Annotated[int, Field(ge=60, le=2520)] = 252


# ---- Hedge finder -----------------------------------------------------------


class HedgeCandidate(_BaseModel):
    """One ranked hedge ticker for a given sector concentration."""

    ticker: str
    name: str
    kind: str  # "etf" | "stock"
    universe_sector: str
    correlation: float = Field(
        ge=-1.0,
        le=1.0,
        description=(
            "Pearson correlation between this candidate's daily returns and "
            "the user's concentrated-sector basket over the lookback window. "
            "Strongly negative = effective hedge historically."
        ),
    )
    half_life_warning: bool = Field(
        default=False,
        description=(
            "True when the trailing 6-month correlation differs from the "
            "full-window correlation by more than 0.30 — flags relationships "
            "that have weakened or flipped recently."
        ),
    )
    recent_correlation: float = Field(
        ge=-1.0,
        le=1.0,
        description=(
            "Trailing ~6-month Pearson correlation. Compared against the "
            "full-window value to detect regime shifts."
        ),
    )


class SectorHedgeSuggestion(_BaseModel):
    """Hedge candidates ranked for one concentrated sector in the user's book."""

    sector: str
    sector_weight: float = Field(
        ge=0.0, le=1.0,
        description="Weight of this sector in the user's portfolio.",
    )
    candidates: list[HedgeCandidate]


class HedgeSuggestRequest(_BaseModel):
    holdings: list[Holding] = Field(min_length=1, max_length=200)
    lookback_days: Annotated[int, Field(ge=60, le=2520)] = 504
    top_k: Annotated[int, Field(ge=1, le=20)] = 5
    # Only consider sectors above this user-book weight as worth hedging.
    min_sector_weight: Annotated[float, Field(ge=0.0, le=1.0)] = 0.25


class HedgeSuggestResponse(_BaseModel):
    suggestions: list[SectorHedgeSuggestion]
    universe_size: int
    lookback_days: int
    disclaimer: str = Field(
        default=(
            "Historical correlations may not hold in future regimes. "
            "Hedge suggestions are based on past data only and are not "
            "investment advice. Always do your own research."
        ),
    )
    limitations: list[str] = Field(default_factory=list)


# ---- Peer comparison --------------------------------------------------------


class PeerCandidate(_BaseModel):
    """One similar-sentiment peer for the reference ticker."""

    ticker: str
    name: str
    sector: str
    kind: str
    correlation: float = Field(
        ge=-1.0, le=1.0,
        description="Pearson correlation of daily returns with the reference.",
    )
    spot: float | None = Field(
        default=None,
        description="Current spot price; None when fetch failed.",
    )
    market_cap: float | None = None
    same_industry: bool = Field(
        default=False,
        description="True when the peer's industry matches the reference.",
    )
    is_cheaper: bool = Field(
        default=False,
        description=(
            "True when this peer is materially smaller-cap than the "
            "reference — proxy for 'cheaper-but-similar'."
        ),
    )


class PeerComparisonResponse(_BaseModel):
    reference_ticker: str
    reference_name: str | None
    reference_sector: str | None
    reference_industry: str | None
    reference_spot: float | None
    reference_market_cap: float | None
    peers: list[PeerCandidate]
    universe_size: int
    lookback_days: int
    limitations: list[str] = Field(default_factory=list)
