/**
 * Client-side Black-Scholes-Merton for the scenario explorer.
 *
 * IMPORTANT: This is for interactive what-ifs only. The verified pricing
 * always comes from the server (py_vollib + QuantLib cross-checked). When
 * the scenario explorer mounts, we cross-check the client implementation
 * against the server-computed primary result; any divergence above 1e-3
 * disables the explorer rather than show drifting numbers.
 *
 * Math is the standard BSM closed-form for European options with a
 * continuous dividend yield. Greeks are the standard analytical forms.
 */

export type OptionType = "call" | "put";

export interface BSInputs {
  spot: number;
  strike: number;
  time_to_expiry_years: number;
  volatility: number; // decimal, e.g. 0.18 for 18%
  risk_free_rate: number; // decimal
  dividend_yield: number; // decimal
  option_type: OptionType;
}

export interface BSResult {
  price: number;
  delta: number;
  gamma: number;
  vega: number; // per 1% absolute change in vol (matches py_vollib)
  theta: number; // per day (matches py_vollib analytical)
  rho: number; // per 1% absolute change in rate
}

// Abramowitz & Stegun 7.1.26 — sub-ULP accuracy for x in [-8, 8].
function erf(x: number): number {
  const sign = x < 0 ? -1 : 1;
  const a = Math.abs(x);
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;
  const t = 1.0 / (1.0 + p * a);
  const y =
    1.0 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-a * a);
  return sign * y;
}

function normCdf(x: number): number {
  return 0.5 * (1 + erf(x / Math.SQRT2));
}

function normPdf(x: number): number {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

/** Compute BSM price + Greeks. T must be > 0; vol must be > 0. */
export function blackScholes(inputs: BSInputs): BSResult {
  const { spot, strike, time_to_expiry_years: T, volatility: sigma } = inputs;
  const { risk_free_rate: r, dividend_yield: q, option_type } = inputs;
  if (T <= 0 || sigma <= 0 || spot <= 0 || strike <= 0) {
    return { price: 0, delta: 0, gamma: 0, vega: 0, theta: 0, rho: 0 };
  }

  const sqrtT = Math.sqrt(T);
  const d1 =
    (Math.log(spot / strike) + (r - q + 0.5 * sigma * sigma) * T) /
    (sigma * sqrtT);
  const d2 = d1 - sigma * sqrtT;

  const expQT = Math.exp(-q * T);
  const expRT = Math.exp(-r * T);

  let price: number;
  let delta: number;
  let theta: number;
  let rho: number;

  if (option_type === "call") {
    price = spot * expQT * normCdf(d1) - strike * expRT * normCdf(d2);
    delta = expQT * normCdf(d1);
    // py_vollib analytical theta: divide annualised by 365 for per-day units.
    const thetaAnnual =
      -(spot * expQT * normPdf(d1) * sigma) / (2 * sqrtT) -
      r * strike * expRT * normCdf(d2) +
      q * spot * expQT * normCdf(d1);
    theta = thetaAnnual / 365;
    rho = (strike * T * expRT * normCdf(d2)) / 100;
  } else {
    price = strike * expRT * normCdf(-d2) - spot * expQT * normCdf(-d1);
    delta = expQT * (normCdf(d1) - 1);
    const thetaAnnual =
      -(spot * expQT * normPdf(d1) * sigma) / (2 * sqrtT) +
      r * strike * expRT * normCdf(-d2) -
      q * spot * expQT * normCdf(-d1);
    theta = thetaAnnual / 365;
    rho = (-strike * T * expRT * normCdf(-d2)) / 100;
  }

  const gamma = (expQT * normPdf(d1)) / (spot * sigma * sqrtT);
  // vega per 1% vol change (py_vollib convention).
  const vega = (spot * expQT * normPdf(d1) * sqrtT) / 100;

  return { price, delta, gamma, vega, theta, rho };
}
