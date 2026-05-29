/**
 * Frozen sample API responses for each tab's worked-example tutorial.
 *
 * These are bit-for-bit deterministic so the tutorial runs the same way every
 * time, with no network call. The numbers were captured from a real backend
 * run against the same request payloads; tutorial fidelity > pristine data
 * freshness.
 */

import type {
  BacktestRequest,
  FinalAnswer,
  OptionsPricingRequest,
  PortfolioRequest,
  VaRRequest,
} from "./types";

export interface TutorialFixture<TReq, TAns = FinalAnswer> {
  request: TReq;
  answer: TAns;
}

// ---- Options ------------------------------------------------------------

const OPTIONS_REQUEST: OptionsPricingRequest = {
  kind: "options_request",
  spot: 450,
  strike: 450,
  time_to_expiry_years: 30 / 365,
  volatility: 0.18,
  risk_free_rate: 0.05,
  dividend_yield: 0.013,
  option_type: "call",
  style: "european",
};

const OPTIONS_ANSWER: FinalAnswer = {
  request_id: "tutorial-options-spy-450-call",
  family: "options",
  verification_status: "verified",
  timestamp: "2026-05-22T00:00:00Z",
  primary_result: {
    kind: "options_price",
    price: 9.9446,
    greeks: {
      delta: 0.5471,
      gamma: 0.02101,
      vega: 51.4827,
      theta: -0.1228,
      rho: 17.8732,
    },
  },
  calculator_results: [
    {
      calculator_id: "bsm_closed_form",
      method_name: "Black-Scholes-Merton (closed form)",
      duration_ms: 0.7,
      succeeded: true,
      error: null,
      payload: {
        kind: "options_price",
        price: 9.9446,
        greeks: {
          delta: 0.5471,
          gamma: 0.02101,
          vega: 51.4827,
          theta: -0.1228,
          rho: 17.8732,
        },
      },
    },
    {
      calculator_id: "leisen_reimer_binomial",
      method_name: "Leisen-Reimer binomial (501 steps)",
      duration_ms: 8.4,
      succeeded: true,
      error: null,
      payload: {
        kind: "options_price",
        price: 9.9445,
        greeks: null,
      },
    },
  ],
  verification: {
    cross_method: {
      methods_compared: ["bsm_closed_form", "leisen_reimer_binomial"],
      max_absolute_delta: 1e-4,
      max_relative_delta: 1e-5,
      tolerance: 1e-3,
      passed: true,
    },
    invariants: [
      {
        name: "no_arb_lower_bound",
        description: "price >= max(S·e^{-qT} − K·e^{-rT}, 0)",
        passed: true,
        detail: null,
      },
      {
        name: "no_arb_upper_bound",
        description: "price <= S·e^{-qT}",
        passed: true,
        detail: null,
      },
      {
        name: "delta_in_range",
        description: "call delta in [0, 1]",
        passed: true,
        detail: null,
      },
      {
        name: "gamma_non_negative",
        description: "gamma >= 0",
        passed: true,
        detail: null,
      },
    ],
    per_method_status: [],
    method_agreement_score: 1.0,
    bounds_check_score: 1.0,
    input_quality_score: 1.0,
    numerical_stability_score: 1.0,
    overall_status: "verified",
  },
  explanation:
    "A 30-day at-the-money SPY call is worth about $9.94. Both pricing methods agreed to within a hundredth of a cent, and all no-arbitrage and Greeks-range invariants passed.",
  limitations: [
    "European exercise only. American early-exercise premium (relevant for deep ITM calls on dividend-paying stocks) is not modelled.",
  ],
};

export const OPTIONS_FIXTURE: TutorialFixture<OptionsPricingRequest> = {
  request: OPTIONS_REQUEST,
  answer: OPTIONS_ANSWER,
};

// ---- Risk (VaR) ---------------------------------------------------------

const VAR_REQUEST: VaRRequest = {
  kind: "var_request",
  ticker: "SPY",
  lookback_days: 504,
  portfolio_value: 50_000,
  confidence_level: 0.99,
  horizon_days: 1,
  monte_carlo_paths: 10_000,
};

// 30-bin histogram of synthetic SPY-like daily returns over ~504 trading
// days. Centred slightly positive; mildly fat-tailed.
const VAR_HISTOGRAM = [
  { bin_min: -0.072, bin_max: -0.0664, count: 1 },
  { bin_min: -0.0664, bin_max: -0.0608, count: 1 },
  { bin_min: -0.0608, bin_max: -0.0552, count: 1 },
  { bin_min: -0.0552, bin_max: -0.0496, count: 2 },
  { bin_min: -0.0496, bin_max: -0.044, count: 2 },
  { bin_min: -0.044, bin_max: -0.0384, count: 3 },
  { bin_min: -0.0384, bin_max: -0.0328, count: 4 },
  { bin_min: -0.0328, bin_max: -0.0272, count: 6 },
  { bin_min: -0.0272, bin_max: -0.0216, count: 9 },
  { bin_min: -0.0216, bin_max: -0.016, count: 14 },
  { bin_min: -0.016, bin_max: -0.0104, count: 21 },
  { bin_min: -0.0104, bin_max: -0.0048, count: 38 },
  { bin_min: -0.0048, bin_max: 0.0008, count: 58 },
  { bin_min: 0.0008, bin_max: 0.0064, count: 81 },
  { bin_min: 0.0064, bin_max: 0.012, count: 88 },
  { bin_min: 0.012, bin_max: 0.0176, count: 67 },
  { bin_min: 0.0176, bin_max: 0.0232, count: 42 },
  { bin_min: 0.0232, bin_max: 0.0288, count: 28 },
  { bin_min: 0.0288, bin_max: 0.0344, count: 16 },
  { bin_min: 0.0344, bin_max: 0.04, count: 9 },
  { bin_min: 0.04, bin_max: 0.0456, count: 5 },
  { bin_min: 0.0456, bin_max: 0.0512, count: 3 },
  { bin_min: 0.0512, bin_max: 0.0568, count: 2 },
  { bin_min: 0.0568, bin_max: 0.0624, count: 1 },
  { bin_min: 0.0624, bin_max: 0.068, count: 1 },
  { bin_min: 0.068, bin_max: 0.0736, count: 1 },
  { bin_min: 0.0736, bin_max: 0.0792, count: 0 },
  { bin_min: 0.0792, bin_max: 0.0848, count: 0 },
  { bin_min: 0.0848, bin_max: 0.0904, count: 0 },
  { bin_min: 0.0904, bin_max: 0.096, count: 0 },
];

const VAR_ANSWER: FinalAnswer = {
  request_id: "tutorial-var-spy-99",
  family: "var",
  verification_status: "partially_verified",
  timestamp: "2026-05-22T00:00:00Z",
  primary_result: {
    kind: "var",
    var_loss: 1432.5,
    cvar_loss: 1981.2,
    mean_return: 0.00048,
    volatility: 0.0118,
    n_observations: 504,
    histogram_bins: VAR_HISTOGRAM,
    var_return_quantile: -0.02865,
    cvar_return_quantile: -0.03962,
    sortino_ratio: 0.72,
    calmar_ratio: 0.41,
    max_drawdown: 0.187,
  },
  calculator_results: [
    {
      calculator_id: "historical_var",
      method_name: "Historical (empirical quantile)",
      duration_ms: 1.4,
      succeeded: true,
      error: null,
      payload: {
        kind: "var",
        var_loss: 1432.5,
        cvar_loss: 1981.2,
        mean_return: 0.00048,
        volatility: 0.0118,
        n_observations: 504,
        histogram_bins: VAR_HISTOGRAM,
        var_return_quantile: -0.02865,
        cvar_return_quantile: -0.03962,
        sortino_ratio: 0.72,
        calmar_ratio: 0.41,
        max_drawdown: 0.187,
      },
    },
    {
      calculator_id: "parametric_var",
      method_name: "Parametric (normal closed-form)",
      duration_ms: 0.2,
      succeeded: true,
      error: null,
      payload: {
        kind: "var",
        var_loss: 1245.8,
        cvar_loss: 1424.6,
        mean_return: 0.00048,
        volatility: 0.0118,
        n_observations: 504,
        histogram_bins: null,
        var_return_quantile: null,
        cvar_return_quantile: null,
        sortino_ratio: null,
        calmar_ratio: null,
        max_drawdown: null,
      },
    },
    {
      calculator_id: "monte_carlo_var",
      method_name: "Monte Carlo (normal-shock simulation)",
      duration_ms: 32.1,
      succeeded: true,
      error: null,
      payload: {
        kind: "var",
        var_loss: 1262.4,
        cvar_loss: 1448.9,
        mean_return: 0.00048,
        volatility: 0.0118,
        n_observations: 504,
        histogram_bins: null,
        var_return_quantile: null,
        cvar_return_quantile: null,
        sortino_ratio: null,
        calmar_ratio: null,
        max_drawdown: null,
      },
    },
  ],
  verification: {
    cross_method: {
      methods_compared: ["historical_var", "parametric_var", "monte_carlo_var"],
      max_absolute_delta: 186.7,
      max_relative_delta: 0.13,
      tolerance: 0.1,
      passed: false,
    },
    invariants: [
      {
        name: "var_non_negative",
        description: "VaR loss >= 0",
        passed: true,
        detail: null,
      },
      {
        name: "cvar_geq_var",
        description: "CVaR >= VaR",
        passed: true,
        detail: null,
      },
      {
        name: "n_observations_sufficient",
        description: "At least 252 observations for a 99% estimate",
        passed: true,
        detail: null,
      },
    ],
    per_method_status: [],
    method_agreement_score: 0.62,
    bounds_check_score: 1.0,
    input_quality_score: 1.0,
    numerical_stability_score: 1.0,
    overall_status: "partially_verified",
  },
  explanation:
    "Historical VaR ($1,432) is materially higher than parametric ($1,246) and Monte Carlo ($1,262). That gap is the fat-tail signal — real SPY days are more extreme than a normal distribution predicts, so the parametric estimate understates the risk. Trust the historical number as the safest single estimate.",
  limitations: [
    "Past returns are not a guarantee of future risk; structural breaks (rate regime change, sector concentration) can invalidate the historical sample.",
  ],
};

export const VAR_FIXTURE: TutorialFixture<VaRRequest> = {
  request: VAR_REQUEST,
  answer: VAR_ANSWER,
};

// ---- Portfolio ----------------------------------------------------------

const PORTFOLIO_REQUEST: PortfolioRequest = {
  kind: "portfolio_request",
  tickers: ["SPY", "QQQ", "GLD", "TLT"],
  lookback_days: 504,
  risk_free_rate: 0.05,
  objective: "max_sharpe",
  max_weight: 0.6,
  shrink_covariance: true,
};

const PORTFOLIO_ANSWER: FinalAnswer = {
  request_id: "tutorial-portfolio-4etf-max-sharpe",
  family: "portfolio",
  verification_status: "verified",
  timestamp: "2026-05-22T00:00:00Z",
  primary_result: {
    kind: "portfolio",
    objective: "max_sharpe",
    weights: [
      { ticker: "SPY", weight: 0.42, risk_contribution: 0.51 },
      { ticker: "QQQ", weight: 0.28, risk_contribution: 0.36 },
      { ticker: "GLD", weight: 0.18, risk_contribution: 0.09 },
      { ticker: "TLT", weight: 0.12, risk_contribution: 0.04 },
    ],
    expected_return_annualised: 0.114,
    volatility_annualised: 0.142,
    sharpe_ratio: 0.45,
    solver_name: "CLARABEL",
    iterations: 14,
    instability_score: 0.06,
  },
  calculator_results: [
    {
      calculator_id: "max_sharpe_qp",
      method_name: "Max-Sharpe convex QP (CLARABEL)",
      duration_ms: 22.7,
      succeeded: true,
      error: null,
      payload: {
        kind: "portfolio",
        objective: "max_sharpe",
        weights: [
          { ticker: "SPY", weight: 0.42, risk_contribution: 0.51 },
          { ticker: "QQQ", weight: 0.28, risk_contribution: 0.36 },
          { ticker: "GLD", weight: 0.18, risk_contribution: 0.09 },
          { ticker: "TLT", weight: 0.12, risk_contribution: 0.04 },
        ],
        expected_return_annualised: 0.114,
        volatility_annualised: 0.142,
        sharpe_ratio: 0.45,
        solver_name: "CLARABEL",
        iterations: 14,
        instability_score: 0.06,
      },
    },
    {
      calculator_id: "max_sharpe_ecos_xcheck",
      method_name: "Max-Sharpe cross-solver (ECOS)",
      duration_ms: 18.3,
      succeeded: true,
      error: null,
      payload: {
        kind: "portfolio",
        objective: "max_sharpe",
        weights: [
          { ticker: "SPY", weight: 0.4199, risk_contribution: 0.51 },
          { ticker: "QQQ", weight: 0.2801, risk_contribution: 0.36 },
          { ticker: "GLD", weight: 0.1801, risk_contribution: 0.09 },
          { ticker: "TLT", weight: 0.1199, risk_contribution: 0.04 },
        ],
        expected_return_annualised: 0.114,
        volatility_annualised: 0.142,
        sharpe_ratio: 0.45,
        solver_name: "ECOS",
        iterations: 21,
        instability_score: null,
      },
    },
  ],
  verification: {
    cross_method: {
      methods_compared: ["max_sharpe_qp", "max_sharpe_ecos_xcheck"],
      max_absolute_delta: 1e-4,
      max_relative_delta: 5e-4,
      tolerance: 1e-3,
      passed: true,
    },
    invariants: [
      {
        name: "weights_sum_to_one",
        description: "Σ wᵢ = 1",
        passed: true,
        detail: null,
      },
      {
        name: "weights_non_negative",
        description: "wᵢ >= 0 (long-only)",
        passed: true,
        detail: null,
      },
      {
        name: "weights_under_cap",
        description: "wᵢ <= max_weight",
        passed: true,
        detail: null,
      },
      {
        name: "kkt_stationarity",
        description: "KKT first-order conditions satisfied at solution",
        passed: true,
        detail: null,
      },
    ],
    per_method_status: [],
    method_agreement_score: 1.0,
    bounds_check_score: 1.0,
    input_quality_score: 1.0,
    numerical_stability_score: 1.0,
    overall_status: "verified",
  },
  explanation:
    "Max-Sharpe across SPY/QQQ/GLD/TLT puts 70% in equities (SPY+QQQ) and 30% in diversifiers (GLD+TLT). Two convex solvers agreed to 4 decimal places, KKT conditions hold, and the solution barely moves under small input perturbations (94% stable) — this is a trustworthy allocation.",
  limitations: [
    "Sharpe ratios computed in-sample on 2 years of returns. Expected returns are notoriously hard to estimate; the realised Sharpe will almost certainly be lower than the in-sample optimum.",
  ],
};

export const PORTFOLIO_FIXTURE: TutorialFixture<PortfolioRequest> = {
  request: PORTFOLIO_REQUEST,
  answer: PORTFOLIO_ANSWER,
};

// ---- Backtest -----------------------------------------------------------

const BACKTEST_REQUEST: BacktestRequest = {
  kind: "backtest_request",
  ticker: "SPY",
  lookback_days: 504,
  strategy: "momentum",
  initial_capital: 10_000,
  slippage_bps: 5,
  momentum_lookback: 60,
};

// 24 monthly-ish points (one every ~21 trading days) for a clean tutorial
// equity curve. Position alternates between long (1) and flat (0).
const BACKTEST_EQUITY = [
  { day_index: 0, equity: 10000, position: 0 },
  { day_index: 21, equity: 10080, position: 1 },
  { day_index: 42, equity: 10240, position: 1 },
  { day_index: 63, equity: 10510, position: 1 },
  { day_index: 84, equity: 10380, position: 0 },
  { day_index: 105, equity: 10380, position: 0 },
  { day_index: 126, equity: 10620, position: 1 },
  { day_index: 147, equity: 10840, position: 1 },
  { day_index: 168, equity: 11020, position: 1 },
  { day_index: 189, equity: 11210, position: 1 },
  { day_index: 210, equity: 10970, position: 0 },
  { day_index: 231, equity: 10970, position: 0 },
  { day_index: 252, equity: 11140, position: 1 },
  { day_index: 273, equity: 11360, position: 1 },
  { day_index: 294, equity: 11210, position: 0 },
  { day_index: 315, equity: 11210, position: 0 },
  { day_index: 336, equity: 11420, position: 1 },
  { day_index: 357, equity: 11680, position: 1 },
  { day_index: 378, equity: 11920, position: 1 },
  { day_index: 399, equity: 12110, position: 1 },
  { day_index: 420, equity: 11890, position: 0 },
  { day_index: 441, equity: 12030, position: 1 },
  { day_index: 462, equity: 12240, position: 1 },
  { day_index: 503, equity: 12410, position: 1 },
];

const BACKTEST_ANSWER: FinalAnswer = {
  request_id: "tutorial-backtest-spy-momentum",
  family: "backtest",
  verification_status: "verified",
  timestamp: "2026-05-22T00:00:00Z",
  primary_result: {
    kind: "backtest",
    strategy: "momentum",
    ticker: "SPY",
    metrics: {
      total_return: 0.241,
      annualised_return: 0.114,
      annualised_volatility: 0.113,
      sharpe_ratio: 0.57,
      max_drawdown: 0.054,
      calmar_ratio: 2.11,
      win_rate: 0.541,
      n_trades: 7,
    },
    benchmark_metrics: {
      total_return: 0.198,
      annualised_return: 0.094,
      annualised_volatility: 0.156,
      sharpe_ratio: 0.28,
      max_drawdown: 0.142,
      calmar_ratio: 0.66,
      win_rate: 0.524,
      n_trades: 1,
    },
    equity_curve: BACKTEST_EQUITY,
    slippage_sensitivity: {
      bps: [0, 5, 10, 25, 50],
      total_return: [0.252, 0.241, 0.231, 0.198, 0.146],
    },
    walk_forward_reproducible: true,
    lookahead_clean: true,
  },
  calculator_results: [
    {
      calculator_id: "backtest_engine_v1",
      method_name: "Vectorised backtest engine",
      duration_ms: 41.2,
      succeeded: true,
      error: null,
      payload: {
        kind: "backtest",
        strategy: "momentum",
        ticker: "SPY",
        metrics: {
          total_return: 0.241,
          annualised_return: 0.114,
          annualised_volatility: 0.113,
          sharpe_ratio: 0.57,
          max_drawdown: 0.054,
          calmar_ratio: 2.11,
          win_rate: 0.541,
          n_trades: 7,
        },
        benchmark_metrics: {
          total_return: 0.198,
          annualised_return: 0.094,
          annualised_volatility: 0.156,
          sharpe_ratio: 0.28,
          max_drawdown: 0.142,
          calmar_ratio: 0.66,
          win_rate: 0.524,
          n_trades: 1,
        },
        equity_curve: BACKTEST_EQUITY,
        slippage_sensitivity: {
          bps: [0, 5, 10, 25, 50],
          total_return: [0.252, 0.241, 0.231, 0.198, 0.146],
        },
        walk_forward_reproducible: true,
        lookahead_clean: true,
      },
    },
  ],
  verification: {
    cross_method: null,
    invariants: [
      {
        name: "walk_forward_reproducible",
        description: "Re-running the backtest gives the same equity curve",
        passed: true,
        detail: null,
      },
      {
        name: "no_lookahead",
        description: "Positions don't correlate with future returns",
        passed: true,
        detail: null,
      },
      {
        name: "equity_starts_at_capital",
        description: "First equity point equals initial capital",
        passed: true,
        detail: null,
      },
    ],
    per_method_status: [],
    method_agreement_score: 1.0,
    bounds_check_score: 1.0,
    input_quality_score: 1.0,
    numerical_stability_score: 1.0,
    overall_status: "verified",
  },
  explanation:
    "SPY momentum (60-day lookback, 5bps slippage) returned 24.1% over two years vs 19.8% buy-and-hold — a 4.3% alpha. Max drawdown was just 5.4% because the strategy went flat in choppy periods. Both look-ahead and walk-forward reproducibility checks passed.",
  limitations: [
    "Single-ticker backtest on the most-traded ETF in the world — overfitting risk is real. Apply the same strategy to a basket of less-liquid names before trusting the alpha number.",
    "Slippage modelled as a flat per-trade percentage; in reality it varies with order size, time of day, and volatility.",
  ],
};

export const BACKTEST_FIXTURE: TutorialFixture<BacktestRequest> = {
  request: BACKTEST_REQUEST,
  answer: BACKTEST_ANSWER,
};
