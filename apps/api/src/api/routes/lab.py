"""Methods Lab API — invoke individual calculators directly, no orchestration.

Two endpoints:

- ``GET /lab/methods`` — list every method (id, name, family, description).
- ``POST /lab/run`` — execute a single method with caller-provided inputs and
  return the raw `CalculatorResult` (no cross-method check, no invariants,
  no sensitivity). Useful for advanced users who want to see what one
  specific method says about a given input.

This is the user-facing surface for the "Methods Lab" tab. The frontend
fetches the catalog via `/lab/methods` to build the picker, then sends a
single `/lab/run` request when the user clicks "Run".

Authoritative dispatch table is the `_REGISTRY` constant below. Adding a
new method = one entry here + the catalog metadata in `kb/catalog.py`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.calculators.backtest.runner import run_backtest
from src.calculators.options import binomial, black_scholes, crank_nicolson, monte_carlo
from src.calculators.portfolio import (
    inverse_vol,
    max_sharpe,
    mean_variance,
    min_variance,
    risk_parity,
)
from src.calculators.risk import (
    bootstrap,
    cornish_fisher,
    historical,
    parametric,
)
from src.calculators.risk import (
    monte_carlo as mc_var,
)
from src.core.schemas import (
    BacktestRequest,
    CalculatorResult,
    OptionsPricingRequest,
    PortfolioRequest,
    VaRRequest,
)
from src.data_providers.market_data import (
    MarketDataError,
    default_provider,
)

router = APIRouter()

# ---- Method registry --------------------------------------------------------

Family = str  # "options" | "var" | "portfolio" | "backtest"


class MethodDescriptor(BaseModel):
    """Public catalog entry for one calculator method."""

    method_id: str
    method_name: str
    family: Family
    one_line: str
    independent_from: list[str]
    cost: str  # "negligible" | "cheap" | "moderate" | "expensive"


# Curated metadata for the lab catalog. Independence claims point at the
# methods this one is most informatively cross-checked against.
_METHODS: list[MethodDescriptor] = [
    # Options ---------------------------------------------------------------
    MethodDescriptor(
        method_id="py_vollib_bsm_closed_form",
        method_name="Black-Scholes-Merton (closed-form, py_vollib)",
        family="options",
        one_line="Analytical closed-form pricing of European calls and puts.",
        independent_from=["quantlib_binomial_lr", "monte_carlo_gbm", "crank_nicolson_pde"],
        cost="negligible",
    ),
    MethodDescriptor(
        method_id="quantlib_binomial_lr",
        method_name="Leisen-Reimer binomial (QuantLib, 801 steps)",
        family="options",
        one_line="Lattice pricing — converges to BSM at O(1/n²) for European vanillas.",
        independent_from=["py_vollib_bsm_closed_form", "monte_carlo_gbm", "crank_nicolson_pde"],
        cost="cheap",
    ),
    MethodDescriptor(
        method_id="monte_carlo_gbm",
        method_name="Monte Carlo (GBM, antithetic, 100k paths)",
        family="options",
        one_line="Sampling-based pricing — independent of analytical / lattice methods.",
        independent_from=["py_vollib_bsm_closed_form", "quantlib_binomial_lr", "crank_nicolson_pde"],
        cost="moderate",
    ),
    MethodDescriptor(
        method_id="crank_nicolson_pde",
        method_name="Crank-Nicolson finite-difference (BS PDE)",
        family="options",
        one_line="Implicit grid solver for the Black-Scholes PDE.",
        independent_from=["py_vollib_bsm_closed_form", "quantlib_binomial_lr", "monte_carlo_gbm"],
        cost="expensive",
    ),
    # VaR -------------------------------------------------------------------
    MethodDescriptor(
        method_id="historical_var",
        method_name="Historical VaR (empirical quantile)",
        family="var",
        one_line="No distributional assumption — reads the loss quantile straight from the sample.",
        independent_from=["parametric_var", "monte_carlo_var", "cornish_fisher_var", "bootstrap_var"],
        cost="negligible",
    ),
    MethodDescriptor(
        method_id="parametric_var",
        method_name="Parametric VaR (normal closed-form)",
        family="var",
        one_line="Closed-form under the Gaussian-returns assumption.",
        independent_from=["historical_var", "monte_carlo_var", "cornish_fisher_var", "bootstrap_var"],
        cost="negligible",
    ),
    MethodDescriptor(
        method_id="monte_carlo_var",
        method_name="Monte Carlo VaR (normal-shock simulation)",
        family="var",
        one_line="Simulation-based under Gaussian assumption.",
        independent_from=["historical_var", "parametric_var", "cornish_fisher_var", "bootstrap_var"],
        cost="cheap",
    ),
    MethodDescriptor(
        method_id="cornish_fisher_var",
        method_name="Cornish-Fisher VaR (skew/kurt-adjusted parametric)",
        family="var",
        one_line="Closed-form with sample skew + excess kurtosis corrections.",
        independent_from=["historical_var", "parametric_var", "monte_carlo_var", "bootstrap_var"],
        cost="negligible",
    ),
    MethodDescriptor(
        method_id="bootstrap_var",
        method_name="Bootstrap historical VaR (1000 resamples)",
        family="var",
        one_line="Resample-with-replacement quantile — captures sample uncertainty.",
        independent_from=["historical_var", "parametric_var", "monte_carlo_var", "cornish_fisher_var"],
        cost="cheap",
    ),
    # Portfolio -------------------------------------------------------------
    MethodDescriptor(
        method_id="mean_variance_qp",
        method_name="Mean-variance utility QP (cvxpy + CLARABEL)",
        family="portfolio",
        one_line="Maximises μᵀw − (γ/2) wᵀΣw, long-only, fully invested.",
        independent_from=["max_sharpe_qp", "risk_parity_log_barrier", "min_variance_qp", "inverse_vol"],
        cost="cheap",
    ),
    MethodDescriptor(
        method_id="max_sharpe_qp",
        method_name="Max-Sharpe tangent portfolio (cvxpy + CLARABEL)",
        family="portfolio",
        one_line="Highest return-per-risk ratio — the classic mean-variance tangent.",
        independent_from=["mean_variance_qp", "risk_parity_log_barrier", "min_variance_qp", "inverse_vol"],
        cost="cheap",
    ),
    MethodDescriptor(
        method_id="risk_parity_log_barrier",
        method_name="Risk parity (Spinu/Maillard log-barrier)",
        family="portfolio",
        one_line="Equal risk contribution from every asset — μ-invariant.",
        independent_from=["mean_variance_qp", "max_sharpe_qp", "min_variance_qp", "inverse_vol"],
        cost="cheap",
    ),
    MethodDescriptor(
        method_id="min_variance_qp",
        method_name="Minimum-variance portfolio (cvxpy + CLARABEL)",
        family="portfolio",
        one_line="Lowest σ portfolio — no return forecast needed.",
        independent_from=["mean_variance_qp", "max_sharpe_qp", "risk_parity_log_barrier", "inverse_vol"],
        cost="cheap",
    ),
    MethodDescriptor(
        method_id="inverse_vol",
        method_name="Inverse-volatility weighting (heuristic)",
        family="portfolio",
        one_line="w_i ∝ 1/σ_i then normalise — closed-form, no solver.",
        independent_from=["mean_variance_qp", "max_sharpe_qp", "risk_parity_log_barrier", "min_variance_qp"],
        cost="negligible",
    ),
    # Backtest --------------------------------------------------------------
    MethodDescriptor(
        method_id="backtest_engine:buy_and_hold",
        method_name="Buy-and-hold (benchmark)",
        family="backtest",
        one_line="Always 100% long — the honest baseline every other strategy must beat.",
        independent_from=[],
        cost="negligible",
    ),
    MethodDescriptor(
        method_id="backtest_engine:ma_crossover",
        method_name="Moving-average crossover",
        family="backtest",
        one_line="Long when fast SMA crosses above slow SMA.",
        independent_from=["backtest_engine:momentum"],
        cost="negligible",
    ),
    MethodDescriptor(
        method_id="backtest_engine:momentum",
        method_name="Momentum (trailing return)",
        family="backtest",
        one_line="Long when the trailing-N-day cumulative return is positive.",
        independent_from=["backtest_engine:ma_crossover"],
        cost="negligible",
    ),
    MethodDescriptor(
        method_id="backtest_engine:mean_reversion",
        method_name="Mean reversion (z-score)",
        family="backtest",
        one_line="Long on price dips beyond −entry_z standard deviations.",
        independent_from=["backtest_engine:momentum", "backtest_engine:ma_crossover"],
        cost="negligible",
    ),
    MethodDescriptor(
        method_id="backtest_engine:bollinger",
        method_name="Bollinger Bands",
        family="backtest",
        one_line="Long when price closes below μ − k·σ; exit at μ.",
        independent_from=["backtest_engine:mean_reversion"],
        cost="negligible",
    ),
]

_REGISTRY: dict[str, MethodDescriptor] = {m.method_id: m for m in _METHODS}


# ---- Endpoints --------------------------------------------------------------


class LabRunRequest(BaseModel):
    method_id: str = Field(..., min_length=1)
    # Inputs are a free-form dict because the schema varies per family.
    # The endpoint validates against the appropriate request model on dispatch.
    inputs: dict[str, Any]
    # For VaR/portfolio/backtest, allow caller to supply returns directly,
    # bypassing the data provider (useful for offline / deterministic runs).
    returns: list[float] | None = None
    returns_matrix: list[list[float]] | None = None


class LabRunResponse(BaseModel):
    method_id: str
    method_name: str
    family: Family
    result: CalculatorResult


@router.get("/methods", response_model=list[MethodDescriptor])
def list_methods() -> list[MethodDescriptor]:
    """Catalog every method available in the lab, grouped by family."""
    return _METHODS


@router.post("/run", response_model=LabRunResponse)
def run_method(req: LabRunRequest) -> LabRunResponse:
    """Invoke a single calculator method with caller-provided inputs."""
    descriptor = _REGISTRY.get(req.method_id)
    if descriptor is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown method_id: {req.method_id!r}"
        )

    try:
        result = _dispatch(descriptor, req)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        # Pydantic / domain validation: surface as 422 so the client knows
        # the inputs were the problem, not the engine.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return LabRunResponse(
        method_id=descriptor.method_id,
        method_name=descriptor.method_name,
        family=descriptor.family,
        result=result,
    )


# ---- Dispatch helpers -------------------------------------------------------


def _dispatch(descriptor: MethodDescriptor, req: LabRunRequest) -> CalculatorResult:
    if descriptor.family == "options":
        return _dispatch_options(descriptor.method_id, req)
    if descriptor.family == "var":
        return _dispatch_var(descriptor.method_id, req)
    if descriptor.family == "portfolio":
        return _dispatch_portfolio(descriptor.method_id, req)
    if descriptor.family == "backtest":
        return _dispatch_backtest(descriptor.method_id, req)
    raise ValueError(f"Unknown family: {descriptor.family!r}")


def _dispatch_options(method_id: str, req: LabRunRequest) -> CalculatorResult:
    payload = OptionsPricingRequest.model_validate(req.inputs)
    if method_id == "py_vollib_bsm_closed_form":
        return black_scholes.compute(payload)
    if method_id == "quantlib_binomial_lr":
        return binomial.compute(payload)
    if method_id == "monte_carlo_gbm":
        return monte_carlo.compute(payload)
    if method_id == "crank_nicolson_pde":
        return crank_nicolson.compute(payload)
    raise ValueError(f"Unknown options method: {method_id}")


def _dispatch_var(method_id: str, req: LabRunRequest) -> CalculatorResult:
    payload = VaRRequest.model_validate(req.inputs)
    returns = req.returns
    if returns is None:
        if payload.returns is not None:
            returns = payload.returns
        elif payload.ticker:
            returns = default_provider().fetch_daily_returns(
                payload.ticker, payload.lookback_days
            )
        else:
            raise ValueError(
                "VaR requires either a `ticker` or an explicit `returns` array"
            )
    if method_id == "historical_var":
        return historical.compute(payload, returns)
    if method_id == "parametric_var":
        return parametric.compute(payload, returns)
    if method_id == "monte_carlo_var":
        return mc_var.compute(payload, returns)
    if method_id == "cornish_fisher_var":
        return cornish_fisher.compute(payload, returns)
    if method_id == "bootstrap_var":
        return bootstrap.compute(payload, returns)
    raise ValueError(f"Unknown VaR method: {method_id}")


def _dispatch_portfolio(method_id: str, req: LabRunRequest) -> CalculatorResult:
    payload = PortfolioRequest.model_validate(req.inputs)
    if req.returns_matrix is not None:
        returns_matrix = np.asarray(req.returns_matrix, dtype=np.float64)
    else:
        _, aligned = default_provider().fetch_aligned_returns(
            payload.tickers, payload.lookback_days
        )
        returns_matrix = np.asarray(aligned, dtype=np.float64)
    if method_id == "mean_variance_qp":
        return mean_variance.compute(payload, returns_matrix)
    if method_id == "max_sharpe_qp":
        return max_sharpe.compute(payload, returns_matrix)
    if method_id == "risk_parity_log_barrier":
        return risk_parity.compute(payload, returns_matrix)
    if method_id == "min_variance_qp":
        return min_variance.compute(payload, returns_matrix)
    if method_id == "inverse_vol":
        return inverse_vol.compute(payload, returns_matrix)
    raise ValueError(f"Unknown portfolio method: {method_id}")


def _dispatch_backtest(method_id: str, req: LabRunRequest) -> CalculatorResult:
    # The backtest engine reads its strategy from BacktestRequest.strategy; we
    # override the request's `strategy` field with the one encoded in
    # `method_id` so the lab caller doesn't have to set both.
    inputs = dict(req.inputs)
    strategy_key = method_id.split(":", 1)[1] if ":" in method_id else None
    if strategy_key is None:
        raise ValueError(f"Backtest method_id must include strategy: {method_id}")
    inputs["strategy"] = strategy_key
    payload = BacktestRequest.model_validate(inputs)
    if req.returns is not None:
        returns_arr = np.asarray(req.returns, dtype=np.float64)
    else:
        returns_arr = np.asarray(
            default_provider().fetch_daily_returns(payload.ticker, payload.lookback_days),
            dtype=np.float64,
        )
    result, _equity, _positions = run_backtest(payload, returns_arr)
    return result
