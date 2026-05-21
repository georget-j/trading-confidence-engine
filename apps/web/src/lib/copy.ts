/**
 * Central plain-English copy for every retail-facing label / tooltip.
 *
 * Tone: neutral retail-friendly. Concrete, no jargon, no slang. One short
 * sentence definition + (where helpful) one example. Edit here, never inline.
 *
 * Convention:
 *   - `label` is the short form shown next to the input.
 *   - `info`  is the tooltip body (what + why).
 */

export interface FieldCopy {
  label: string;
  info: string;
}

export const OPTIONS_INPUTS: Record<string, FieldCopy> = {
  spot: {
    label: "Underlying spot",
    info: "The current price of the underlying stock or index. If the ticker is SPY at $450, spot = 450.",
  },
  strike: {
    label: "Strike",
    info: "The price the option lets you buy (call) or sell (put) at. Profit at expiry depends on where the spot finishes relative to strike.",
  },
  days: {
    label: "Days to expiry",
    info: "Calendar days until the option expires. Shorter expiries are cheaper but lose time value faster.",
  },
  vol: {
    label: "Implied vol",
    info: "The market's bet on how much the underlying will move (annualised, in percent). Higher implied vol → the option costs more. SPY typically sits around 12–20%; meme stocks can be 60%+.",
  },
  rate: {
    label: "Risk-free rate",
    info: "The annual interest rate you could earn risk-free over the option's life (e.g. T-bill yield). Affects pricing modestly except on long-dated options.",
  },
  div: {
    label: "Dividend yield",
    info: "Annual dividend rate of the underlying, as a percent. Calls get cheaper and puts pricier when dividends are higher (the underlying drops on ex-div).",
  },
  optionType: {
    label: "Option type",
    info: "Call = right to BUY at the strike. Put = right to SELL at the strike. Calls profit when the underlying goes up, puts when it goes down.",
  },
};

export const RISK_INPUTS: Record<string, FieldCopy> = {
  ticker: {
    label: "Ticker",
    info: "Stock or ETF symbol. Historical daily returns are fetched and used to estimate how big a one-day loss could realistically be.",
  },
  portfolio: {
    label: "Portfolio value",
    info: "The dollar amount you have invested. VaR is reported as a dollar loss against this amount.",
  },
  lookback: {
    label: "Lookback",
    info: "How much price history to use, in trading days. 504 ≈ 2 years. More history smooths the estimate but reacts slower to a new market regime.",
  },
  confidence: {
    label: "Confidence",
    info: "How extreme a loss you're measuring. 95% = 'a loss this bad happens about 5 days in 100'. 99% = '1 day in 100' — much rarer but much bigger.",
  },
  horizon: {
    label: "Horizon",
    info: "How many days into the future the loss estimate covers. 1 day is the standard. Longer horizons → larger VaR (scaling with √days).",
  },
};

export const GREEKS: Record<string, FieldCopy> = {
  delta: {
    label: "Δ delta",
    info: "If the underlying moves $1, the option moves about delta × $1. Calls have delta in [0, 1]; puts in [-1, 0].",
  },
  gamma: {
    label: "Γ gamma",
    info: "How fast delta itself changes. High gamma means the option's sensitivity flips quickly — a small move in the underlying changes the risk profile a lot.",
  },
  vega: {
    label: "ν vega",
    info: "How much the option price moves when implied vol changes by 1 percentage point. Long-dated and at-the-money options have the most vega.",
  },
  theta: {
    label: "Θ theta",
    info: "Time decay. The dollar amount the option loses per day if nothing else changes. Always negative for long option positions.",
  },
  rho: {
    label: "ρ rho",
    info: "Sensitivity to interest rates. Usually small unless the option has months or years left.",
  },
};

export const OUTPUTS = {
  varLoss: {
    label: "Value at Risk",
    info: "The most you'd expect to lose under the chosen confidence level. A 95% VaR of $200 means: 'on 95 out of 100 days, your loss will be smaller than $200.' On the remaining 5 days, it can be much bigger.",
  },
  cvarLoss: {
    label: "Expected Shortfall (CVaR)",
    info: "When losses DO exceed VaR, this is the average loss you'd take. Always at least as bad as VaR — and often quite a bit worse on fat-tailed assets.",
  },
  optionPrice: {
    label: "Option price",
    info: "Fair theoretical price under Black-Scholes-Merton, cross-checked by a binomial tree. Real market quotes will differ due to bid/ask spread, supply/demand, and dividend timing.",
  },
};

export const VERIFICATION_STATUS = {
  verified: {
    label: "Verified",
    info: "Two independent calculation methods agreed on the result, and every no-arbitrage / consistency check passed. Treat this number as trustworthy within the model's assumptions.",
  },
  partially_verified: {
    label: "Partially verified",
    info: "The methods didn't tightly agree — usually a real signal that the assumptions don't fit your data (e.g. fat tails for VaR). The number is not 'wrong', but the methods disagree by enough that you should treat it as a range, not a point. The most assumption-free method is your safest bet.",
  },
  not_verified: {
    label: "Not verified",
    info: "Either the methods diverged badly or a math invariant failed (e.g. price below the no-arbitrage lower bound). Don't act on this number — the engine is telling you it can't stand behind it.",
  },
};

export const SCORES = {
  method_agreement: {
    label: "Method agreement",
    info: "How closely the independent calculation methods agree with each other. 100% = they match within tight tolerance; 50% = they're in the same ballpark but disagree non-trivially; 0% = real divergence.",
  },
  bounds_check: {
    label: "Invariants",
    info: "Fraction of math identities (no-arbitrage bounds, put-call parity, VaR ≥ 0, etc.) that the result satisfies. Anything below 100% is a hard fail.",
  },
  input_quality: {
    label: "Input quality",
    info: "How clean and complete the inputs were. Fresh market data with no missing fields scores 100%; stale or partial inputs drag this down.",
  },
  numerical_stability: {
    label: "Numerical stability",
    info: "For methods that iterate (binomial trees, optimisers), whether the calculation converged cleanly. 100% means no convergence issues.",
  },
};
