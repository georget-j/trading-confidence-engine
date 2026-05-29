"use client";

/**
 * One-line plain-English summary that sits above every result card.
 *
 * Replaces "lead with a dense 5-column grid" with "lead with a sentence
 * anyone can read". The dense card still renders below for users who want
 * the full numbers.
 *
 * In Simple mode this is the primary thing on screen.
 * In Advanced mode it's just a clearer headline above the existing grid.
 */

import type {
  BacktestPayload,
  FinalAnswer,
  OptionsPriceResult,
  OptionsStrategyPayload,
  PortfolioPayload,
  VaRPayload,
  VerificationStatus,
} from "@/lib/types";

interface Props {
  answer: FinalAnswer;
}

export function ResultSummary({ answer }: Props) {
  const sentence = buildSentence(answer);
  const tone = toneFor(answer.verification_status);
  return (
    <div
      className={`rounded-2xl border p-4 shadow-sm sm:p-5 ${tone.container}`}
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl leading-none" aria-hidden>
          {tone.icon}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm leading-relaxed text-zinc-900 sm:text-base">
            {sentence}
          </p>
          <p
            className={`mt-1 text-xs font-semibold uppercase tracking-wide ${tone.label}`}
          >
            {tone.statusText}
          </p>
        </div>
      </div>
    </div>
  );
}

// --- Sentence builders per family -------------------------------------------

function buildSentence(answer: FinalAnswer): string {
  const p = answer.primary_result;
  if (p.kind === "options_price") return optionsSentence(p);
  if (p.kind === "options_strategy") return strategySentence(p);
  if (p.kind === "var") return varSentence(p);
  if (p.kind === "portfolio") return portfolioSentence(p);
  if (p.kind === "backtest") return backtestSentence(p);
  return answer.explanation;
}

function optionsSentence(p: OptionsPriceResult): string {
  const price = p.price.toFixed(2);
  return `This option is worth about $${price} per contract right now.`;
}

function strategySentence(p: OptionsStrategyPayload): string {
  const net = Math.abs(p.net_premium).toFixed(2);
  const side =
    p.net_premium > 0
      ? `a net debit of $${net}`
      : p.net_premium < 0
        ? `a net credit of $${net}`
        : "an even net premium";
  return `This ${p.legs.length}-leg strategy would cost ${side} per contract today.`;
}

function varSentence(p: VaRPayload): string {
  const var_ = formatUsd(p.var_loss);
  const cvar = formatUsd(p.cvar_loss);
  return `Worst-case daily loss at the chosen confidence level is about ${var_}. On the very worst days, expect to lose ${cvar} on average.`;
}

function portfolioSentence(p: PortfolioPayload): string {
  const top = [...p.weights]
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 2)
    .map((w) => `${w.ticker} ${(w.weight * 100).toFixed(0)}%`)
    .join(" and ");
  const sharpe = p.sharpe_ratio.toFixed(2);
  return `The optimal portfolio leans heavily into ${top}, with a Sharpe ratio of ${sharpe} (higher is better; >1 is good).`;
}

function backtestSentence(p: BacktestPayload): string {
  const total = (p.metrics.total_return * 100).toFixed(1);
  const sign = p.metrics.total_return >= 0 ? "+" : "";
  const dd = (p.metrics.max_drawdown * 100).toFixed(1);
  return `Strategy returned ${sign}${total}% with a worst drawdown of ${dd}%.`;
}

// --- Tone ---------------------------------------------------------------------

function toneFor(status: VerificationStatus) {
  if (status === "verified") {
    return {
      icon: "✓",
      container: "border-emerald-200 bg-emerald-50",
      label: "text-emerald-800",
      statusText: "✓ Verified — independent methods agreed",
    };
  }
  if (status === "partially_verified") {
    return {
      icon: "⚠",
      container: "border-amber-200 bg-amber-50",
      label: "text-amber-800",
      statusText: "⚠ Partially verified — methods diverged",
    };
  }
  return {
    icon: "✗",
    container: "border-rose-200 bg-rose-50",
    label: "text-rose-800",
    statusText: "✗ Not verified — don't act on this number",
  };
}

function formatUsd(v: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
}
