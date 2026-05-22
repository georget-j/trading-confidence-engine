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

export const STRATEGY_INPUTS: Record<string, FieldCopy> = {
  optionType: {
    label: "Type",
    info: "Call or put for this leg. Mix freely — e.g. an iron condor has two of each.",
  },
  strike: {
    label: "Strike",
    info: "The price the option lets you trade at. Per-leg, so vertical spreads (different strikes) and condors (four strikes) are first-class.",
  },
  quantity: {
    label: "Qty",
    info: "Signed number of contracts. Positive = long (you paid premium). Negative = short (you collected premium).",
  },
  days: {
    label: "Days",
    info: "Per-leg days to expiry. Same across legs for verticals/condors; different for calendar spreads.",
  },
  vol: {
    label: "IV %",
    info: "Per-leg implied vol. Same across legs unless you want to model a vol skew (e.g. higher IV on OTM puts).",
  },
};

export const STRATEGY_OUTPUTS = {
  netPremium: {
    label: "Net premium",
    info: "Sum of (quantity × leg price). Positive = net debit (you pay). Negative = net credit (you collect). Max loss for credit positions is the spread width minus the credit received.",
  },
  netGreeks: {
    label: "Net Greeks",
    info: "Quantity-weighted sum of each leg's Greeks. Tells you the strategy's overall sensitivity to spot, vol, and time — net delta near zero means the position is direction-neutral at the current spot.",
  },
};

export const PORTFOLIO_INPUTS: Record<string, FieldCopy> = {
  tickers: {
    label: "Tickers",
    info: "Comma-separated stock or ETF symbols (2 to 20). The optimiser allocates weights across all of them.",
  },
  lookback: {
    label: "Lookback",
    info: "How much price history to use, in trading days. 504 ≈ 2 years. Longer histories smooth the covariance estimate but slow your response to a regime shift.",
  },
  riskFree: {
    label: "Risk-free rate",
    info: "Annual interest rate you could earn risk-free (e.g. T-bill yield). Used to compute the Sharpe ratio and the max-Sharpe objective.",
  },
  objective: {
    label: "Objective",
    info: "Mean-variance maximises return minus a γ·risk penalty (you control γ). Max-Sharpe finds the tangent portfolio with the highest reward-per-unit-risk ratio. Risk parity ignores expected returns entirely and weights so every asset contributes equally to portfolio variance — robust against mean-return estimation error.",
  },
  riskAversion: {
    label: "Risk aversion γ",
    info: "Mean-variance only. Higher γ → more weight on reducing variance → more diversified portfolio. Typical retail values: 2–5.",
  },
  maxWeight: {
    label: "Max per asset",
    info: "Cap on any single position. 40% means no asset can exceed 40% of the portfolio. Without this constraint, mean-variance often concentrates 100% in the single best-performing in-sample asset — a textbook over-fitting failure.",
  },
  shrinkCovariance: {
    label: "Robust covariance",
    info: "Ledoit-Wolf shrinkage towards constant-correlation. Reduces over-fitting to the noisy sample covariance. Recommended on; disable only if you understand the trade-off.",
  },
};

export const PORTFOLIO_OUTPUTS = {
  weight: {
    label: "Weight",
    info: "Fraction of the portfolio allocated to this asset. Weights are non-negative (long-only) and sum to 100%.",
  },
  riskContribution: {
    label: "Risk contribution",
    info: "Share of total portfolio variance attributable to this asset. A 30% weight that contributes 60% of risk is a concentration warning — the asset's volatility/correlation dominates the portfolio.",
  },
  sharpe: {
    label: "Sharpe ratio",
    info: "Excess return per unit of volatility. (E[r] − rf) / σ. Higher is better. 1.0 is good, 2.0 is exceptional, anything from in-sample optimisation should be treated as an upper bound.",
  },
  expectedReturn: {
    label: "E[r]",
    info: "Expected annualised return of the optimal portfolio under the lookback's sample mean. In-sample number — the realised return will almost certainly be different (usually lower).",
  },
  volatility: {
    label: "σ",
    info: "Annualised volatility of the optimal portfolio (standard deviation of returns). Lower σ for the same E[r] is what the optimiser is trying to achieve.",
  },
  instability: {
    label: "Solution stability",
    info: "How much the optimal weights move under a small (±1%) perturbation of expected returns. 100% = perfectly stable. Anything below 75% means the weights are noise-driven and you should diversify the inputs rather than trust the exact allocation.",
  },
};

export const PORTFOLIO_OBJECTIVE_LABEL: Record<string, string> = {
  mean_variance: "Mean-variance",
  max_sharpe: "Max-Sharpe",
  risk_parity: "Risk parity",
};

export const BACKTEST_OUTPUTS = {
  totalReturn: {
    label: "Total return",
    info: "Cumulative return over the whole backtest window, after slippage. Compounded — a 24% total return on $10k means the account ended at $12,400.",
  },
  annualisedReturn: {
    label: "Ann. return",
    info: "Total return converted to a per-year rate. Lets you compare backtests of different lengths on a like-for-like basis.",
  },
  annualisedVolatility: {
    label: "Ann. vol",
    info: "Annualised standard deviation of daily returns. Equities typically run 12–25%; a strategy with lower vol than buy-and-hold is taking less risk.",
  },
  sharpe: {
    label: "Sharpe",
    info: "Excess return per unit of volatility. >1 is good, >2 is exceptional. In-sample numbers should be discounted — out-of-sample Sharpe is usually meaningfully lower.",
  },
  maxDrawdown: {
    label: "Max DD",
    info: "Worst peak-to-trough loss on the equity curve. Tells you the worst pain you would have sat through holding this strategy.",
  },
  calmar: {
    label: "Calmar",
    info: "Annualised return divided by max drawdown. High Calmar = small drawdown relative to returns. Sample-dependent — a backtest that never saw a big crash will overstate Calmar.",
  },
  winRate: {
    label: "Win rate",
    info: "Fraction of trades that closed profitably. A 30% win rate can still be highly profitable if winners are much larger than losers — don't read this in isolation.",
  },
  nTrades: {
    label: "Trades",
    info: "Number of round-trip trades the strategy made. More trades = more slippage cost and more statistical confidence; fewer trades = lower cost but less signal.",
  },
  walkForward: {
    label: "Walk-forward reproducible",
    info: "Running the exact same backtest twice produces bit-identical results. A hard requirement for trustworthy audit logs — if this fails, there's hidden randomness in the engine.",
  },
  lookahead: {
    label: "No look-ahead bias",
    info: "Positions don't peek at future returns. Look-ahead is the #1 way backtest results lie — the engine detects it by checking whether your positions correlate suspiciously with returns from days ahead.",
  },
  slippageBps: {
    label: "Slippage (bps)",
    info: "Per-trade trading-cost penalty in basis points (1 bp = 0.01%). 5 bps ≈ retail equity costs; 25 bps is what unfriendly fills cost you. Sweep this column to see how cost-sensitive the strategy is.",
  },
  alpha: {
    label: "Alpha (return)",
    info: "Extra return over passively holding the underlying (total return − buy-and-hold total return). Positive alpha means the active rules added value over doing nothing.",
  },
};

export const BACKTEST_STRATEGY_LABEL: Record<string, string> = {
  buy_and_hold: "Buy & hold",
  ma_crossover: "Moving-average crossover",
  momentum: "Momentum",
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
  sortino: {
    label: "Sortino",
    info: "Like Sharpe but only penalises downside moves — large positive returns don't count as 'risk.' Computed from the same returns sample. 1.0 is decent, 2.0+ is unusually clean. Always higher than Sharpe.",
  },
  calmar: {
    label: "Calmar",
    info: "Annualised return divided by the worst peak-to-trough drawdown in the sample. High Calmar = returns dwarf the worst loss seen. Beware: sample drawdowns understate true risk.",
  },
  maxDrawdown: {
    label: "Max drawdown",
    info: "Worst peak-to-trough decline in the cumulative return series over the lookback. A −18% max drawdown means at some point the underlying lost 18% from its high before recovering (or not).",
  },
  nObservations: {
    label: "N observations",
    info: "Number of daily returns used in the calculation. More observations smooth the estimate but react slower to a new regime. A 99% VaR estimate needs at least ~250 observations to even see ~2-3 'tail' days.",
  },
  meanReturn: {
    label: "Mean return",
    info: "Average daily return over the lookback sample. Usually tiny (a few basis points). Equity means are notoriously noisy — don't read too much into a single sample.",
  },
  sampleVolatility: {
    label: "Volatility",
    info: "Standard deviation of daily returns over the lookback sample. Annualised volatility ≈ daily × √252. Equities typically run 12–25% annualised.",
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

export interface GlossaryEntry {
  term: string;
  short: string;
  long: string;
  alsoSee?: string[];
}

/** Terms most likely to confuse a retail user, ordered roughly by how often
 *  they appear in the UI. */
export const GLOSSARY: GlossaryEntry[] = [
  {
    term: "Verified",
    short: "Two independent methods agreed AND every invariant passed.",
    long: "The engine cross-checks every result with at least two independent calculators (different math, different codebases) and runs no-arbitrage / consistency checks. 'Verified' means everything lined up. It does NOT mean the market will behave this way — just that the model is internally consistent.",
  },
  {
    term: "Partially verified",
    short: "Methods disagreed enough to be flagged, but not catastrophically.",
    long: "Real-world data often has 'fat tails' (extreme moves more often than a normal distribution predicts). When that happens, parametric (normal-assumption) results diverge from historical (no-assumption) results — both are individually correct under their own assumptions, but they're answering slightly different questions. Trust the historical method as the safest single number.",
    alsoSee: ["Fat tails"],
  },
  {
    term: "Not verified",
    short: "Methods disagreed badly or a math invariant failed.",
    long: "Either the calculation methods diverged beyond the wide tolerance, or a mathematical identity (e.g. a price below the no-arbitrage lower bound) was violated. The engine refuses to claim a number it can't stand behind.",
  },
  {
    term: "Implied volatility (IV)",
    short: "The market's expectation of how much the underlying will move.",
    long: "Annualised, in percent. Derived from option prices, not from historical prices. Higher IV → options cost more. SPY typically sits at 12–20%; meme stocks can be 60%+; FX usually 5–10%.",
  },
  {
    term: "Delta (Δ)",
    short: "How much the option moves per $1 in the underlying.",
    long: "Calls have delta in [0, 1]; puts in [-1, 0]. An at-the-money call has delta around 0.5: if the underlying moves up $1, the option gains about $0.50.",
    alsoSee: ["Gamma"],
  },
  {
    term: "Gamma (Γ)",
    short: "How fast delta itself changes.",
    long: "High gamma means the option's sensitivity flips quickly — a small move in the underlying changes the risk profile a lot. Always non-negative for vanilla calls and puts.",
    alsoSee: ["Delta"],
  },
  {
    term: "Vega (ν)",
    short: "Sensitivity to a change in implied vol.",
    long: "How much the option price moves per 1-percentage-point change in implied vol. Long-dated, at-the-money options carry the most vega.",
  },
  {
    term: "Theta (Θ)",
    short: "Time decay — what you lose per day if nothing else changes.",
    long: "Always negative for long option positions. Short-dated at-the-money options decay fastest near expiry.",
  },
  {
    term: "Rho (ρ)",
    short: "Sensitivity to a change in the risk-free rate.",
    long: "Usually small. Matters mostly on long-dated (months/years) options.",
  },
  {
    term: "Value at Risk (VaR)",
    short: "The most you'd expect to lose under a given confidence level.",
    long: "A 95% VaR of $200 means: on 95 out of 100 days, your loss will be smaller than $200. On the remaining 5 days, the loss can be much larger — VaR does not bound the maximum loss.",
    alsoSee: ["Expected Shortfall (CVaR)"],
  },
  {
    term: "Expected Shortfall (CVaR)",
    short: "The average loss on days when losses exceed VaR.",
    long: "Always at least as bad as VaR — often quite a bit worse on fat-tailed assets. A useful 'when things go wrong, here's the typical magnitude' number.",
    alsoSee: ["Value at Risk (VaR)"],
  },
  {
    term: "Fat tails",
    short:
      "Real returns have more extreme moves than a normal distribution predicts.",
    long: "If returns were perfectly normal, a -5% day would happen once every ~30 years. In reality, equities see -5% days every few years. Parametric (normal-assumption) VaR understates real risk on fat-tailed assets; historical VaR captures it (within the limits of the sample).",
  },
  {
    term: "No-arbitrage bounds",
    short: "Hard mathematical limits no option price can violate.",
    long: "For a call: price ≥ max(S·e^{-qT} − K·e^{-rT}, 0) and price ≤ S·e^{-qT}. Mirror conditions hold for puts. Violation means money-for-nothing exists, which means the price is wrong.",
  },
  {
    term: "Parametric VaR",
    short:
      "VaR computed using a closed-form formula under the normal assumption.",
    long: "Fast and smooth, but biased when real returns aren't normal. Compare against historical VaR — if they diverge, the normal assumption is the suspect.",
    alsoSee: ["Historical VaR", "Fat tails"],
  },
  {
    term: "Historical VaR",
    short:
      "VaR computed directly from past returns — no distributional assumption.",
    long: "The most honest single number when real returns are non-normal. Limited by the sample (95% VaR on 252 trading days only sees ~13 'worst' days).",
    alsoSee: ["Parametric VaR"],
  },
  {
    term: "Monte Carlo VaR",
    short: "VaR estimated by simulating many random return paths.",
    long: "Sampling-based: numerically distinct from both closed-form and historical. Useful as an independent third method. We use a fixed random seed so identical inputs reproduce exactly.",
  },
];

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
