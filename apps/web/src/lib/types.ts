// Mirror of the FastAPI Pydantic schemas. Kept in lock-step manually for now;
// V4 of the plan introduces auto-generated types from the OpenAPI spec.

export type OptionType = "call" | "put";
export type OptionStyle = "european" | "american";
export type VerificationStatus =
  | "verified"
  | "partially_verified"
  | "not_verified";

export interface OptionsPricingRequest {
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
}

export type PortfolioObjective = "mean_variance" | "max_sharpe";

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

export interface VerificationResult {
  cross_method: CrossMethodCheck | null;
  invariants: InvariantCheck[];
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
