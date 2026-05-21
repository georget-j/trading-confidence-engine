"""Method catalog — what every verified calculator does, when to trust it,
and how it is checked.

This is the V4-lightweight knowledge base. The full Postgres + pgvector
version arrives in V8 when saved workflows need durable cross-run state.
For now, the catalog is a typed in-memory list: easy to extend, queryable
by the UI, and unit-tested as part of the regular suite.

Every entry answers four questions a retail user might ask:
  - What does this method actually compute?
  - When does it work, and when does it break?
  - How expensive is one call?
  - How is the answer verified?
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from src.core.schemas import CalcFamily


class Cost(StrEnum):
    NEGLIGIBLE = "negligible"  # < 1ms
    CHEAP = "cheap"  # < 100ms
    MODERATE = "moderate"  # < 1s
    EXPENSIVE = "expensive"  # > 1s


class MethodEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    calculator_id: str
    family: CalcFamily
    method_name: str
    one_line: str = Field(description="Single-sentence retail-friendly summary.")
    long_description: str
    inputs_required: list[str]
    domain_of_validity: list[str] = Field(
        description="When this method works well — bullet points.",
    )
    domain_limits: list[str] = Field(
        description="When this method breaks or is biased — bullet points.",
    )
    invariants_checked: list[str] = Field(
        description="Identities the verifier confirms after every call.",
    )
    cost: Cost
    independent_methods: list[str] = Field(
        default_factory=list,
        description=(
            "Other calculators that solve the same problem and cross-check this one. "
            "Empty list means this method is the only one in its lane."
        ),
    )


METHOD_CATALOG: list[MethodEntry] = [
    # ---- Options pricing ----
    MethodEntry(
        calculator_id="py_vollib_bsm_closed_form",
        family=CalcFamily.OPTIONS_PRICING,
        method_name="Black-Scholes-Merton closed-form (py_vollib)",
        one_line=(
            "The textbook BSM price and Greeks for a European option, via the "
            "py_vollib library."
        ),
        long_description=(
            "Computes the exact Black-Scholes-Merton fair price and analytical "
            "first/second-order Greeks (delta, gamma, vega, theta, rho) under "
            "the standard assumptions: lognormal underlying, constant volatility "
            "and rates, no transaction costs, European exercise. The closed-form "
            "is machine-precision exact within the model — the only error is in "
            "the model's distance from reality."
        ),
        inputs_required=["spot", "strike", "expiry", "vol", "rate", "dividend yield", "call/put"],
        domain_of_validity=[
            "Vanilla European options on liquid underlyings",
            "Time to expiry > a few days",
            "Implied vol in a normal trading range (5–200%)",
        ],
        domain_limits=[
            "Assumes constant volatility — real IV has term structure and skew",
            "American exercise needs the binomial tree (which we run alongside)",
            "Discrete dividends are approximated as a continuous yield",
        ],
        invariants_checked=[
            "Non-negative price",
            "No-arbitrage lower bound: C ≥ max(S·e^(-qT) - K·e^(-rT), 0)",
            "No-arbitrage upper bound: C ≤ S·e^(-qT)",
            "Delta in [0,1] for calls, [-1,0] for puts",
            "Gamma ≥ 0",
            "Put-call parity (when both legs priced)",
        ],
        cost=Cost.NEGLIGIBLE,
        independent_methods=["quantlib_binomial_lr"],
    ),
    MethodEntry(
        calculator_id="quantlib_binomial_lr",
        family=CalcFamily.OPTIONS_PRICING,
        method_name="Leisen-Reimer binomial tree, 801 steps (QuantLib)",
        one_line=(
            "Numerical binomial pricer using the fast-converging Leisen-Reimer "
            "scheme — independent of the closed-form."
        ),
        long_description=(
            "Builds a recombining lattice with Leisen-Reimer probabilities "
            "(O(1/n²) convergence vs CRR's O(1/n)) and back-induces from the "
            "expiry payoff. At 801 steps prices match Black-Scholes-Merton to "
            "~1e-5 for typical inputs. Both calculators feed canonical-T-rounded "
            "inputs so they price the SAME problem rather than differing by "
            "day-count rounding."
        ),
        inputs_required=["spot", "strike", "expiry", "vol", "rate", "dividend yield", "call/put"],
        domain_of_validity=[
            "Same as Black-Scholes-Merton",
            "Handles American exercise (currently unused for verification)",
        ],
        domain_limits=[
            "Binomial discretization can be noisy at extreme parameter combos",
            "Slower than closed-form (~5ms vs <1ms)",
        ],
        invariants_checked=["Same as Black-Scholes-Merton"],
        cost=Cost.CHEAP,
        independent_methods=["py_vollib_bsm_closed_form"],
    ),
    # ---- VaR ----
    MethodEntry(
        calculator_id="historical_var",
        family=CalcFamily.RISK_METRICS,
        method_name="Historical (empirical-quantile) VaR",
        one_line="Reads the worst-N% return directly from the data — no distributional assumption.",
        long_description=(
            "Sorts the observed daily returns and reads off the empirical "
            "quantile at the chosen confidence level. CVaR is the mean of the "
            "tail beyond that quantile. The honest baseline: doesn't assume "
            "normality, but is limited by the sample (95% VaR on 252 days only "
            "sees ~13 tail observations)."
        ),
        inputs_required=["daily returns or ticker+lookback", "confidence", "horizon", "portfolio value"],
        domain_of_validity=[
            "Sufficient history (≥30 observations; recommended ≥252)",
            "Returns reasonably stationary over the lookback window",
        ],
        domain_limits=[
            "Cannot estimate beyond observed-tail extremity",
            "Recent regime changes show up slowly",
        ],
        invariants_checked=["VaR ≥ 0", "CVaR ≥ VaR", "VaR ≤ portfolio value"],
        cost=Cost.NEGLIGIBLE,
        independent_methods=["parametric_var", "monte_carlo_var"],
    ),
    MethodEntry(
        calculator_id="parametric_var",
        family=CalcFamily.RISK_METRICS,
        method_name="Parametric (normal-assumption) VaR",
        one_line="Closed-form VaR assuming returns are normally distributed.",
        long_description=(
            "Fits μ and σ from the data, then computes VaR = -(μ + σ·Φ⁻¹(α)). "
            "CVaR has a closed form for the normal: μ - σ·φ(z)/(1-α). Fast and "
            "smooth, but biased on fat-tailed assets — which is most equities. "
            "Divergence from the historical method is itself a useful signal."
        ),
        inputs_required=["daily returns or ticker+lookback", "confidence", "horizon", "portfolio value"],
        domain_of_validity=[
            "Smooth low-noise estimates",
            "Useful as a baseline for extrapolation",
        ],
        domain_limits=[
            "Underestimates risk on fat-tailed assets",
            "Sensitive to outliers in the mean estimate",
        ],
        invariants_checked=["VaR ≥ 0", "CVaR ≥ VaR", "VaR ≤ portfolio value"],
        cost=Cost.NEGLIGIBLE,
        independent_methods=["historical_var", "monte_carlo_var"],
    ),
    MethodEntry(
        calculator_id="monte_carlo_var",
        family=CalcFamily.RISK_METRICS,
        method_name="Monte Carlo (normal-shock) VaR",
        one_line="VaR estimated by simulating 100k random return paths.",
        long_description=(
            "Independent third method: draws shocks from N(μ, σ²) and reads "
            "the empirical quantile of the simulated distribution. Uses a fixed "
            "seed (0xC0FFEE) so the same inputs reproduce identical outputs "
            "— required for audit-log replayability."
        ),
        inputs_required=["daily returns or ticker+lookback", "confidence", "horizon", "portfolio value", "paths"],
        domain_of_validity=[
            "Catches sampling-noise bugs the closed-form formula would miss",
            "Easily generalises to non-normal distributions",
        ],
        domain_limits=[
            "Sampling error ~1/√N at the tail (~3e-3 at 100k paths)",
            "Currently uses a normal shock — fat-tailed distributions need a different draw",
        ],
        invariants_checked=["VaR ≥ 0", "CVaR ≥ VaR", "VaR ≤ portfolio value"],
        cost=Cost.CHEAP,
        independent_methods=["historical_var", "parametric_var"],
    ),
    # ---- Portfolio ----
    MethodEntry(
        calculator_id="mean_variance_qp",
        family=CalcFamily.PORTFOLIO_OPTIMIZATION,
        method_name="Mean-variance utility maximisation (cvxpy QP)",
        one_line=(
            "Long-only convex QP that maximises expected return minus γ·variance, "
            "with optional position caps and Ledoit-Wolf shrinkage."
        ),
        long_description=(
            "Solves max μᵀw − (γ/2)wᵀΣw s.t. w ≥ 0, 1ᵀw = 1, plus optional box "
            "constraints on individual weights. Defaults bias the result toward "
            "diversification: max_weight=40% and Ledoit-Wolf shrinkage on. "
            "Without these, mean-variance over-fits to in-sample noise and "
            "concentrates in a single asset — a textbook failure mode."
        ),
        inputs_required=["tickers", "lookback", "rf", "γ", "max_weight"],
        domain_of_validity=[
            "Diversified baskets (3+ assets, ideally low-correlation)",
            "Stable correlation regime over lookback",
        ],
        domain_limits=[
            "Highly sensitive to expected-return estimates (estimation error problem)",
            "Out-of-sample performance always worse than in-sample",
        ],
        invariants_checked=[
            "Weights finite, ≥ 0, ≤ max_weight",
            "Weights sum to 1",
            "Risk contributions sum to 1",
            "KKT stationarity (active/lower/upper-bound consistency)",
        ],
        cost=Cost.MODERATE,
        independent_methods=["max_sharpe_qp"],
    ),
    MethodEntry(
        calculator_id="max_sharpe_qp",
        family=CalcFamily.PORTFOLIO_OPTIMIZATION,
        method_name="Max-Sharpe via convex reformulation (cvxpy QP)",
        one_line="Long-only portfolio with the highest in-sample reward-per-risk ratio.",
        long_description=(
            "Solves the tangent-portfolio problem max (μ - rf·1)ᵀw / √(wᵀΣw) via "
            "Cornuejols & Tütüncü's change of variables: introduce y, κ ≥ 0 with "
            "(μ - rf·1)ᵀy = 1 and κ = 1ᵀy, then minimise yᵀΣy. Recovered weights "
            "are y/κ. Box constraints translate as y_i ≤ M·κ. Falls back to "
            "min-variance when no asset has positive excess return."
        ),
        inputs_required=["tickers", "lookback", "rf", "max_weight"],
        domain_of_validity=[
            "Same as mean-variance",
            "At least one asset with E[r] > rf",
        ],
        domain_limits=[
            "Same as mean-variance",
            "Even more sensitive to μ estimates than utility maximisation",
        ],
        invariants_checked=["Same as mean-variance (KKT applies only to MV; for max-Sharpe see cross-solver agreement)"],
        cost=Cost.MODERATE,
        independent_methods=["mean_variance_qp"],
    ),
]
