// Mirror of the FastAPI Pydantic schemas. Kept in lock-step manually for now;
// V4 of the plan introduces auto-generated types from the OpenAPI spec.

export type OptionType = "call" | "put";
export type OptionStyle = "european" | "american";
export type VerificationStatus =
  | "verified"
  | "partially_verified"
  | "not_verified";

export interface OptionsPricingRequest {
  // `kind` mirrors the Pydantic discriminator; defaulted on the backend so
  // clients can continue to omit it.
  kind?: "options_request";
  spot: number;
  strike: number;
  time_to_expiry_years: number;
  volatility: number;
  risk_free_rate: number;
  dividend_yield: number;
  option_type: OptionType;
  style: OptionStyle;
}

export interface Greeks {
  delta: number;
  gamma: number;
  vega: number;
  theta: number;
  rho: number;
}

export interface OptionsPriceResult {
  kind: "options_price";
  price: number;
  greeks: Greeks | null;
}

// ---- Multi-leg strategy ----

export interface StrategyLeg {
  option_type: OptionType;
  strike: number;
  quantity: number; // signed: +N long, -N short
  time_to_expiry_years: number;
  volatility: number;
}

export interface OptionsStrategyRequest {
  kind?: "options_strategy_request";
  spot: number;
  risk_free_rate: number;
  dividend_yield?: number;
  style?: OptionStyle;
  legs: StrategyLeg[];
}

export interface StrategyLegResult {
  option_type: OptionType;
  strike: number;
  quantity: number;
  time_to_expiry_years: number;
  volatility: number;
  price: number;
  greeks: Greeks | null;
}

export interface OptionsStrategyPayload {
  kind: "options_strategy";
  legs: StrategyLegResult[];
  net_premium: number;
  net_greeks: Greeks;
}

export interface HistogramBin {
  bin_min: number;
  bin_max: number;
  count: number;
}

export interface VaRPayload {
  kind: "var";
  var_loss: number;
  cvar_loss: number;
  mean_return: number;
  volatility: number;
  n_observations: number;
  histogram_bins: HistogramBin[] | null;
  var_return_quantile: number | null;
  cvar_return_quantile: number | null;
  sortino_ratio: number | null;
  calmar_ratio: number | null;
  max_drawdown: number | null;
}

export type PortfolioObjective = "mean_variance" | "max_sharpe" | "risk_parity";

export interface AssetWeight {
  ticker: string;
  weight: number;
  risk_contribution: number;
}

export interface PortfolioPayload {
  kind: "portfolio";
  objective: PortfolioObjective;
  weights: AssetWeight[];
  expected_return_annualised: number;
  volatility_annualised: number;
  sharpe_ratio: number;
  solver_name: string;
  iterations: number | null;
  instability_score: number | null;
}

// ---- Backtest ----

export type BacktestStrategy = "buy_and_hold" | "ma_crossover" | "momentum";

export interface BacktestMetrics {
  total_return: number;
  annualised_return: number;
  annualised_volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  calmar_ratio: number;
  win_rate: number;
  n_trades: number;
}

export interface EquityPoint {
  day_index: number;
  equity: number;
  position: number;
}

export interface SlippageSensitivity {
  bps: number[];
  total_return: number[];
}

export interface BacktestPayload {
  kind: "backtest";
  strategy: BacktestStrategy;
  ticker: string;
  metrics: BacktestMetrics;
  benchmark_metrics: BacktestMetrics | null;
  equity_curve: EquityPoint[];
  slippage_sensitivity: SlippageSensitivity;
  walk_forward_reproducible: boolean;
  lookahead_clean: boolean;
}

export interface BacktestRequest {
  kind?: "backtest_request";
  ticker: string;
  lookback_days?: number;
  strategy?: BacktestStrategy;
  initial_capital?: number;
  slippage_bps?: number;
  ma_fast?: number;
  ma_slow?: number;
  momentum_lookback?: number;
}

export type CalcResultPayload =
  | OptionsPriceResult
  | OptionsStrategyPayload
  | VaRPayload
  | PortfolioPayload
  | BacktestPayload;

export interface CalculatorResult {
  calculator_id: string;
  method_name: string;
  payload: CalcResultPayload;
  duration_ms: number;
  succeeded: boolean;
  error: string | null;
}

export interface CrossMethodCheck {
  methods_compared: string[];
  max_absolute_delta: number;
  max_relative_delta: number;
  tolerance: number;
  passed: boolean;
}

export interface InvariantCheck {
  name: string;
  description: string;
  passed: boolean;
  detail: string | null;
}

export type AgreementStatus = "agrees" | "diverges" | "n/a";

export interface PerMethodStatus {
  method_id: string;
  method_name: string;
  ran: boolean;
  value: number | null;
  agreement_status: AgreementStatus;
  divergent_against: string[];
  invariants_passed: string[];
  invariants_failed: string[];
  sensitivity_passed: boolean | null;
  duration_ms: number | null;
  error: string | null;
}

export interface VerificationResult {
  cross_method: CrossMethodCheck | null;
  invariants: InvariantCheck[];
  per_method_status: PerMethodStatus[];
  method_agreement_score: number;
  bounds_check_score: number;
  input_quality_score: number;
  numerical_stability_score: number;
  overall_status: VerificationStatus;
}

export interface FinalAnswer {
  request_id: string;
  family: string;
  verification_status: VerificationStatus;
  primary_result: CalcResultPayload;
  calculator_results: CalculatorResult[];
  verification: VerificationResult;
  explanation: string;
  limitations: string[];
  timestamp: string;
}

// ---- VaR request ----

export interface VaRRequest {
  kind?: "var_request";
  ticker?: string | null;
  lookback_days?: number;
  returns?: number[] | null;
  portfolio_value: number;
  confidence_level: number;
  horizon_days: number;
  monte_carlo_paths?: number;
}

// ---- Method catalog ----

export type Cost = "negligible" | "cheap" | "moderate" | "expensive";

export interface MethodEntry {
  calculator_id: string;
  family: string;
  method_name: string;
  one_line: string;
  long_description: string;
  inputs_required: string[];
  domain_of_validity: string[];
  domain_limits: string[];
  invariants_checked: string[];
  cost: Cost;
  independent_methods: string[];
}

// ---- Portfolio request ----

export interface PortfolioRequest {
  kind?: "portfolio_request";
  tickers: string[];
  lookback_days?: number;
  risk_free_rate?: number;
  objective?: PortfolioObjective;
  risk_aversion?: number;
  max_weight?: number;
  min_weight?: number;
  shrink_covariance?: boolean;
}

// ---- Chat / LLM-parsed types ----

export interface LLMOptionsParse {
  spot: number | null;
  strike: number | null;
  time_to_expiry_days: number | null;
  volatility_pct: number | null;
  risk_free_rate_pct: number | null;
  dividend_yield_pct: number | null;
  option_type: OptionType | null;
  style: OptionStyle | null;
  parse_confidence: number;
  parser_notes: string[];
}

export interface ChatParseResponse {
  structured: OptionsPricingRequest | null;
  raw_parse: LLMOptionsParse;
  ready_to_price: boolean;
}

// ---- Per-family chat parses (M3) ----

export interface LLMVaRParse {
  ticker: string | null;
  lookback_days: number | null;
  portfolio_value: number | null;
  confidence_level: number | null;
  horizon_days: number | null;
  parse_confidence: number;
  parser_notes: string[];
}

export interface ChatVaRParseResponse {
  structured: VaRRequest | null;
  raw_parse: LLMVaRParse;
  ready_to_compute: boolean;
}

export interface LLMPortfolioParse {
  tickers: string[] | null;
  lookback_days: number | null;
  objective: PortfolioObjective | null;
  risk_aversion: number | null;
  max_weight: number | null;
  parse_confidence: number;
  parser_notes: string[];
}

export interface ChatPortfolioParseResponse {
  structured: PortfolioRequest | null;
  raw_parse: LLMPortfolioParse;
  ready_to_optimise: boolean;
}

export interface LLMBacktestParse {
  ticker: string | null;
  lookback_days: number | null;
  strategy: BacktestStrategy | null;
  initial_capital: number | null;
  slippage_bps: number | null;
  parse_confidence: number;
  parser_notes: string[];
}

export interface ChatBacktestParseResponse {
  structured: BacktestRequest | null;
  raw_parse: LLMBacktestParse;
  ready_to_run: boolean;
}

/** Discriminated by `family` — what the user is currently working on.
 *  Each family has its own LLM parser endpoint and request schema. */
export type ChatFamily = "options" | "var" | "portfolio" | "backtest";
