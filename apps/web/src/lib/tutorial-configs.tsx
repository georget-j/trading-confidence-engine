/**
 * Per-tab tutorial configurations. Each builder takes the run-example
 * callback (defined in `page.tsx` so it can mutate per-tab state) and a
 * "has run" flag (so callouts only show after the example has run).
 */

import type {
  TutorialTabConfig,
  TutorialTerm,
} from "@/components/TutorialPanel";
import type { CalloutItem } from "@/components/TutorialCallout";

interface BuilderArgs {
  onRun: () => void;
  hasRun: boolean;
}

const OPTIONS_TERMS: TutorialTerm[] = [
  {
    term: "Underlying spot",
    definition:
      "Current price of the stock or ETF behind the option. If SPY trades at $450, spot = 450.",
  },
  {
    term: "Strike",
    definition:
      "The price the contract lets you trade at. A 450 call is the right to buy SPY for $450.",
  },
  {
    term: "Days to expiry",
    definition:
      "Calendar days until the option expires worthless. Shorter expiries cost less but lose value faster.",
  },
  {
    term: "Implied vol (IV)",
    definition:
      "The market's bet on how much the underlying will move, in percent per year. SPY sits at 12–20% in calm regimes; meme stocks can be 60%+.",
  },
  {
    term: "Risk-free rate",
    definition:
      "The annual interest you could earn risk-free (e.g. T-bills) over the option's life.",
  },
  {
    term: "Dividend yield",
    definition:
      "Annual dividend rate of the underlying as a percent. Higher dividends make calls cheaper and puts pricier.",
  },
  {
    term: "Call / Put",
    definition:
      "Call = right to BUY at the strike (profits if the underlying rises). Put = right to SELL (profits if it falls).",
  },
  {
    term: "Delta (Δ)",
    definition:
      "How much the option price moves per $1 move in the underlying. An at-the-money call has delta ≈ 0.50.",
  },
  {
    term: "Gamma (Γ)",
    definition:
      "How fast delta itself changes. High gamma → the option's sensitivity flips quickly with small moves.",
  },
  {
    term: "Vega (ν)",
    definition:
      "How much the option moves per 1-point change in implied vol. Long-dated at-the-money options have the most vega.",
  },
  {
    term: "Theta (Θ)",
    definition:
      "Time decay — what a long option loses per day if nothing else changes. Always negative for buyers.",
  },
  {
    term: "Rho (ρ)",
    definition:
      "Sensitivity to the risk-free rate. Usually small for short-dated options.",
  },
  {
    term: "Black-Scholes-Merton",
    definition:
      "The standard closed-form formula for European option prices. Gives one of the two numbers we cross-check.",
  },
  {
    term: "Binomial tree",
    definition:
      "An independent pricing method that simulates a tree of up/down moves. The other number we cross-check against.",
  },
  {
    term: "Verified badge",
    definition:
      "Green = both methods agreed AND no-arbitrage bounds passed. Amber = methods diverged. Red = something failed.",
  },
];

export function buildOptionsTutorialConfig({
  onRun,
  hasRun,
}: BuilderArgs): TutorialTabConfig {
  const callouts: CalloutItem[] = [
    {
      n: 1,
      tone: "indigo",
      title: "Option price: ~$9.94",
      body: "Fair theoretical price under Black-Scholes-Merton, also confirmed by an independent binomial tree. Real market quotes will differ slightly due to bid/ask spreads.",
    },
    {
      n: 2,
      tone: "emerald",
      title: "Verified badge",
      body: "Both pricing methods agreed to four decimal places and every no-arbitrage invariant passed — this number is trustworthy under the model's assumptions.",
    },
    {
      n: 3,
      tone: "indigo",
      title: "Delta ≈ 0.55",
      body: "If SPY moves up $1, this call gains about $0.55. At-the-money calls always sit close to 0.50.",
    },
    {
      n: 4,
      tone: "amber",
      title: "Theta ≈ −0.12",
      body: "Time decay. Holding overnight with nothing else changing costs you about $0.12 per contract.",
    },
    {
      n: 5,
      tone: "indigo",
      title: "Payoff chart",
      body: "Shows your dollar P/L at expiry across spot prices. The hockey-stick shape is the call's classic limited-downside / unlimited-upside profile.",
    },
  ];

  return {
    tab: "options",
    tabName: "Options pricing",
    whatItDoes:
      "Price a single option contract (a call or put). You enter what the option is on, what strike, how far from expiry, and how volatile the market thinks the underlying is — the engine returns a fair price, the five Greeks (sensitivities), and a payoff chart, with every number cross-verified by two independent calculation methods.",
    terms: OPTIONS_TERMS,
    exampleTitle: "Worked example: a 30-day at-the-money SPY call",
    examplePreamble:
      "We'll price the most common retail trade: a call on SPY (the S&P 500 ETF) at the current spot, expiring in 30 days, with implied vol around 18%. Click below — the form fills in, the price computes, and numbered callouts appear next to the result to explain each part.",
    exampleCta: "Walk me through it",
    onRunExample: onRun,
    exampleCallouts: callouts,
    exampleHasRun: hasRun,
  };
}

const RISK_TERMS: TutorialTerm[] = [
  {
    term: "Ticker",
    definition:
      "Stock or ETF symbol. We fetch its historical daily returns and use them to estimate how big a one-day loss could realistically be.",
  },
  {
    term: "Portfolio value",
    definition:
      "How many dollars you have invested. VaR is reported as a dollar loss against this amount.",
  },
  {
    term: "Lookback",
    definition:
      "How many trading days of history to use. 504 ≈ 2 years. More history smooths the estimate but reacts slower to a new market regime.",
  },
  {
    term: "Confidence level",
    definition:
      "How extreme a loss you're measuring. 95% means 'a loss this bad happens roughly 5 days in 100'. 99% means '1 day in 100' — rarer but much bigger.",
  },
  {
    term: "Horizon",
    definition:
      "How many days the estimate covers. 1 day is the standard. Longer horizons → bigger VaR (scaling with √days).",
  },
  {
    term: "Value at Risk (VaR)",
    definition:
      "The biggest loss you'd expect under the chosen confidence. A 99% VaR of $1,400 = 'on 99 out of 100 days, your loss will be smaller than $1,400'. The remaining 1% can be much bigger.",
  },
  {
    term: "Expected Shortfall (CVaR)",
    definition:
      "Average loss on the bad days that DO exceed VaR. Always at least as bad as VaR, often quite a bit worse on fat-tailed assets.",
  },
  {
    term: "Historical method",
    definition:
      "VaR taken directly from past returns — no distribution assumption. The most honest single number when reality isn't normal.",
  },
  {
    term: "Parametric method",
    definition:
      "VaR from a closed-form normal-distribution formula. Fast, smooth, biased downward on fat-tailed assets.",
  },
  {
    term: "Monte Carlo method",
    definition:
      "VaR estimated by simulating thousands of random return paths under a normal assumption. Independent third estimator.",
  },
  {
    term: "Fat tails",
    definition:
      "Real returns have more extreme moves than a normal distribution predicts. If historical and parametric VaR diverge, fat tails are the usual cause.",
  },
  {
    term: "Sortino",
    definition:
      "Like Sharpe but only penalises downside moves. Always at least as good as Sharpe; 1.0 is decent, 2.0+ is unusually clean.",
  },
  {
    term: "Calmar",
    definition:
      "Annualised return divided by worst peak-to-trough drawdown in the sample. High Calmar = returns dwarf the worst loss seen.",
  },
  {
    term: "Max drawdown",
    definition:
      "Worst peak-to-trough decline in the period. A −18% max drawdown means at some point the price fell 18% from its high.",
  },
];

export function buildRiskTutorialConfig({
  onRun,
  hasRun,
}: BuilderArgs): TutorialTabConfig {
  const callouts: CalloutItem[] = [
    {
      n: 1,
      tone: "rose",
      title: "VaR: −$1,432 (one-day, 99%)",
      body: "On 99 out of 100 days, your loss on $50k of SPY will be smaller than $1,432. On the remaining 1%, it can be much worse.",
    },
    {
      n: 2,
      tone: "rose",
      title: "CVaR: −$1,981",
      body: "When losses DO blow through VaR, the average is around $1,981 — meaningfully worse than VaR alone. This is the 'when things go wrong' number.",
    },
    {
      n: 3,
      tone: "amber",
      title: "Partially verified — that's the signal",
      body: "Historical ($1,432) is 14% higher than parametric ($1,246) and Monte Carlo ($1,262). That gap is the fat-tail signal — SPY days are more extreme than a normal curve predicts. Trust historical as the safest single estimate.",
    },
    {
      n: 4,
      tone: "indigo",
      title: "Histogram red bars",
      body: "The red bars are the worst 1% of past days — the ones VaR is estimating. Notice how they extend further left than a smooth normal curve would predict.",
    },
    {
      n: 5,
      tone: "indigo",
      title: "Max drawdown: −18.7%",
      body: "Over the 2-year sample, SPY's worst peak-to-trough decline was 18.7%. VaR measures the typical bad day; drawdown measures the worst case actually seen.",
    },
  ];

  return {
    tab: "risk",
    tabName: "Value at Risk (VaR)",
    whatItDoes:
      "Estimate how big a one-day loss could realistically be on a position. The engine runs three independent methods (historical, parametric, Monte Carlo) against the same return sample. When they disagree, that's usually a real signal about fat tails — not a bug.",
    terms: RISK_TERMS,
    exampleTitle: "Worked example: 99% one-day VaR on $50k of SPY",
    examplePreamble:
      "We'll measure the worst typical one-day loss on $50k of SPY, with 99% confidence, using 2 years of history. The three methods will disagree by ~14% — and that disagreement is the most interesting thing in the result.",
    exampleCta: "Walk me through it",
    onRunExample: onRun,
    exampleCallouts: callouts,
    exampleHasRun: hasRun,
  };
}

const PORTFOLIO_TERMS: TutorialTerm[] = [
  {
    term: "Tickers",
    definition:
      "The basket of stocks/ETFs the optimiser allocates across. 2 to 20 symbols, comma-separated.",
  },
  {
    term: "Lookback",
    definition:
      "How much history (in trading days) the estimator uses to compute means, vols, and correlations. 504 ≈ 2 years.",
  },
  {
    term: "Risk-free rate",
    definition:
      "Annual rate you could earn risk-free (e.g. T-bills). Used in the Sharpe ratio and the max-Sharpe objective.",
  },
  {
    term: "Objective: Mean-variance",
    definition:
      "Maximises expected return minus γ × variance. You pick γ; higher = more diversified.",
  },
  {
    term: "Objective: Max-Sharpe",
    definition:
      "Finds the single portfolio with the best return-per-risk ratio. The classic tangent portfolio.",
  },
  {
    term: "Objective: Risk parity",
    definition:
      "Ignores expected returns entirely. Allocates so every asset contributes equally to portfolio variance — robust against bad return estimates.",
  },
  {
    term: "Risk aversion γ",
    definition:
      "Mean-variance only. Higher γ → more weight on reducing variance → more diversified. Retail values: 2–5.",
  },
  {
    term: "Max per asset",
    definition:
      "Cap on any single weight. Without this, mean-variance often concentrates 100% in the best in-sample asset — classic overfitting.",
  },
  {
    term: "Robust covariance (Ledoit-Wolf)",
    definition:
      "Shrinkage estimator that reduces overfitting in the sample covariance matrix. Recommended on.",
  },
  {
    term: "Weight",
    definition:
      "Fraction of the portfolio in each asset. Weights are long-only (≥ 0) and sum to 100%.",
  },
  {
    term: "Risk contribution",
    definition:
      "Share of total portfolio variance attributable to this asset. A 20% weight that contributes 50% of risk is a concentration warning.",
  },
  {
    term: "Sharpe ratio",
    definition:
      "(Expected return − risk-free rate) / volatility. Higher = better. 1.0 is good, 2.0 is exceptional, in-sample optima are upper bounds.",
  },
  {
    term: "Solution stability",
    definition:
      "How much the weights move under a small (±1%) perturbation of expected returns. 100% = perfectly stable. Below 75% = treat the weights as a direction, not a precise number.",
  },
  {
    term: "KKT conditions",
    definition:
      "Mathematical optimality test for constrained convex problems. The engine checks them automatically — if they fail, the 'optimum' isn't actually optimal.",
  },
];

export function buildPortfolioTutorialConfig({
  onRun,
  hasRun,
}: BuilderArgs): TutorialTabConfig {
  const callouts: CalloutItem[] = [
    {
      n: 1,
      tone: "indigo",
      title: "Sharpe: 0.45",
      body: "Reward per unit of risk for the optimal blend. Higher is better; this number is in-sample so the realised Sharpe will almost certainly be lower.",
    },
    {
      n: 2,
      tone: "emerald",
      title: "Verified badge",
      body: "Two independent convex solvers (CLARABEL and ECOS) agreed to four decimal places, KKT first-order conditions hold, and the solution is stable under input perturbations.",
    },
    {
      n: 3,
      tone: "indigo",
      title: "Weights: 42 / 28 / 18 / 12",
      body: "70% in equities (SPY + QQQ) and 30% in diversifiers (gold + long Treasuries). The optimiser found this balance maximises Sharpe given the 2-year history.",
    },
    {
      n: 4,
      tone: "amber",
      title: "Risk contribution ≠ weight",
      body: "GLD has 18% weight but only contributes 9% of total risk — it's low-correlation with equities. SPY has 42% weight and contributes 51% of risk. Useful concentration check.",
    },
    {
      n: 5,
      tone: "emerald",
      title: "Solution stability: 94%",
      body: "Perturbing expected returns by ±1% barely moves the weights. This allocation is robust — not a knife-edge optimum.",
    },
  ];

  return {
    tab: "portfolio",
    tabName: "Portfolio optimisation",
    whatItDoes:
      "Given a basket of tickers and an objective (best risk-adjusted return, or equal risk contribution, or a manual variance penalty), find the optimal weights. The engine cross-checks two convex solvers, verifies KKT optimality conditions, and stress-tests how much the weights move under small input perturbations.",
    terms: PORTFOLIO_TERMS,
    exampleTitle: "Worked example: max-Sharpe across SPY / QQQ / GLD / TLT",
    examplePreamble:
      "We'll optimise a classic 4-ETF basket — US large-cap, US tech, gold, long Treasuries — for the best Sharpe ratio using 2 years of returns. The result will show the optimal weights, the risk contribution of each asset, and a stability score.",
    exampleCta: "Walk me through it",
    onRunExample: onRun,
    exampleCallouts: callouts,
    exampleHasRun: hasRun,
  };
}

const BACKTEST_TERMS: TutorialTerm[] = [
  {
    term: "Ticker",
    definition:
      "The single stock or ETF the strategy trades. Backtests are intentionally single-ticker — easier to interpret.",
  },
  {
    term: "Lookback",
    definition:
      "How many trading days of history to backtest over. 504 ≈ 2 years.",
  },
  {
    term: "Strategy: Buy & hold",
    definition:
      "Position = 100% long on day 1, never touched. The honest benchmark every other strategy has to beat.",
  },
  {
    term: "Strategy: MA crossover",
    definition:
      "Long when a fast moving average crosses above a slow one; flat otherwise. Classic trend-following toy.",
  },
  {
    term: "Strategy: Momentum",
    definition:
      "Long when the trailing N-day return is positive; flat when it's negative. Simple and surprisingly resilient.",
  },
  {
    term: "Slippage (bps)",
    definition:
      "Per-trade trading-cost penalty, in basis points (1 bp = 0.01%). 5 bps ≈ retail equity costs; 25 bps is what unfriendly fills cost you.",
  },
  {
    term: "Initial capital",
    definition:
      "Starting dollar amount. Doesn't change the strategy logic, just the equity-curve scale.",
  },
  {
    term: "Total return",
    definition:
      "Cumulative return over the whole backtest window. Includes all trades and slippage.",
  },
  {
    term: "Annualised return",
    definition:
      "Total return converted to a per-year rate so windows of different lengths are comparable.",
  },
  {
    term: "Sharpe ratio",
    definition:
      "Excess return per unit of volatility. >1 is good, >2 is exceptional, in-sample numbers should be discounted.",
  },
  {
    term: "Max drawdown",
    definition:
      "Worst peak-to-trough loss in the equity curve. Tells you the worst pain you'd have sat through.",
  },
  {
    term: "Win rate",
    definition:
      "Fraction of trades that closed profitably. Note: a 30% win rate can still be highly profitable if winners are bigger than losers.",
  },
  {
    term: "Walk-forward reproducibility",
    definition:
      "Running the exact same backtest twice gives bit-identical results. Hard requirement for trustworthy audit logs.",
  },
  {
    term: "Look-ahead bias",
    definition:
      "Using information that wasn't available at decision time. The engine detects it by checking if positions correlate suspiciously with future returns.",
  },
  {
    term: "Equity curve",
    definition:
      "Your account balance day by day. Grey-shaded bands are days the strategy was flat (out of the market).",
  },
  {
    term: "Slippage sensitivity",
    definition:
      "How total return changes as you raise the per-trade cost. A steep drop means most of the strategy's headline number is eaten by frictions.",
  },
];

export function buildBacktestTutorialConfig({
  onRun,
  hasRun,
}: BuilderArgs): TutorialTabConfig {
  const callouts: CalloutItem[] = [
    {
      n: 1,
      tone: "emerald",
      title: "Total return: +24.1%",
      body: "Compounded return over the 2-year window, after the assumed 5 bps per-trade slippage. The buy-and-hold benchmark below shows what you'd have made just holding SPY.",
    },
    {
      n: 2,
      tone: "indigo",
      title: "Sharpe: 0.57 (vs 0.28 buy-and-hold)",
      body: "Reward per unit of risk. The momentum strategy roughly doubled the buy-and-hold Sharpe by going flat in choppy periods.",
    },
    {
      n: 3,
      tone: "emerald",
      title: "Max drawdown: just 5.4%",
      body: "The worst peak-to-trough loss was tiny because the strategy stepped out of the market during the rough patch (visible as grey shaded bands in the equity curve below).",
    },
    {
      n: 4,
      tone: "indigo",
      title: "Equity curve grey bands",
      body: "Each grey band is a stretch where the strategy was flat (no SPY position). Notice how they line up with the periods where the line stops climbing.",
    },
    {
      n: 5,
      tone: "amber",
      title: "Slippage sensitivity",
      body: "At 0 bps slippage the strategy returns 25.2%. At 50 bps it drops to 14.6%. A real broker would be somewhere between — keep an eye on this column when assessing alpha.",
    },
    {
      n: 6,
      tone: "emerald",
      title: "Both verification flags green",
      body: "Walk-forward reproducibility = re-running gives bit-identical results. No look-ahead bias = positions don't peek at future returns. Both passed.",
    },
  ];

  return {
    tab: "backtest",
    tabName: "Backtest",
    whatItDoes:
      "Replay a simple rules-based trading strategy against historical price data and see how it would have done. The engine reports total return, Sharpe, max drawdown, and stress-tests the result against trading frictions and look-ahead bias — so you can tell apart real edge from accidental hindsight.",
    terms: BACKTEST_TERMS,
    exampleTitle: "Worked example: SPY momentum (60-day lookback)",
    examplePreamble:
      "We'll backtest a simple momentum rule on SPY over 2 years: long when the trailing 60-day return is positive, flat otherwise, with 5 bps per-trade slippage. The strategy beats buy-and-hold partly by avoiding choppy stretches — the equity curve below makes that visible.",
    exampleCta: "Walk me through it",
    onRunExample: onRun,
    exampleCallouts: callouts,
    exampleHasRun: hasRun,
  };
}
