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
  price: number;
  greeks: Greeks | null;
}

export interface CalculatorResult {
  calculator_id: string;
  method_name: string;
  payload: OptionsPriceResult;
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
  primary_result: OptionsPriceResult;
  calculator_results: CalculatorResult[];
  verification: VerificationResult;
  explanation: string;
  limitations: string[];
  timestamp: string;
}
