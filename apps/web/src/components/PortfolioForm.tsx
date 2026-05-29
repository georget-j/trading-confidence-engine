"use client";

import { useState } from "react";
import { PORTFOLIO_INPUTS } from "@/lib/copy";
import type { PortfolioObjective, PortfolioRequest } from "@/lib/types";
import { InfoTooltip } from "./InfoTooltip";

interface Props {
  onSubmit: (req: PortfolioRequest) => void;
  loading: boolean;
}

const OBJECTIVES: { value: PortfolioObjective; label: string }[] = [
  { value: "mean_variance", label: "Mean-variance" },
  { value: "max_sharpe", label: "Max-Sharpe" },
  { value: "risk_parity", label: "Risk parity" },
];

export function PortfolioForm({ onSubmit, loading }: Props) {
  const [tickers, setTickers] = useState("SPY, QQQ, GLD, TLT");
  const [lookback, setLookback] = useState("504");
  const [riskFree, setRiskFree] = useState("4");
  const [objective, setObjective] =
    useState<PortfolioObjective>("mean_variance");
  const [riskAversion, setRiskAversion] = useState("2");
  const [maxWeight, setMaxWeight] = useState("40");
  const [shrinkCovariance, setShrinkCovariance] = useState(true);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const list = tickers
      .split(/[,\s]+/)
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);
    onSubmit({
      tickers: list,
      lookback_days: parseInt(lookback, 10),
      risk_free_rate: parseFloat(riskFree) / 100,
      objective,
      risk_aversion: parseFloat(riskAversion),
      max_weight: parseFloat(maxWeight) / 100,
      shrink_covariance: shrinkCovariance,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <div className="flex items-center text-xs font-medium text-zinc-600">
          <label>{PORTFOLIO_INPUTS.tickers.label}</label>
          <InfoTooltip body={PORTFOLIO_INPUTS.tickers.info} />
        </div>
        <input
          value={tickers}
          onChange={(e) => setTickers(e.target.value)}
          placeholder="SPY, QQQ, GLD, TLT"
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm uppercase tracking-wide text-zinc-900 outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
          required
        />
        <p className="text-[10px] text-zinc-500">
          Between 2 and 20 tickers, comma-separated. Prices fetched via
          yfinance.
        </p>
      </div>

      <div className="space-y-1">
        <div className="flex items-center text-xs font-medium text-zinc-600">
          <label>{PORTFOLIO_INPUTS.objective.label}</label>
          <InfoTooltip body={PORTFOLIO_INPUTS.objective.info} />
        </div>
        <div className="inline-flex rounded-lg border border-zinc-300 p-0.5">
          {OBJECTIVES.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setObjective(opt.value)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                objective === opt.value
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-600 hover:bg-zinc-100"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <NumField
          label={PORTFOLIO_INPUTS.lookback.label}
          info={PORTFOLIO_INPUTS.lookback.info}
          value={lookback}
          onChange={setLookback}
          suffix="d"
        />
        <NumField
          label={PORTFOLIO_INPUTS.riskFree.label}
          info={PORTFOLIO_INPUTS.riskFree.info}
          value={riskFree}
          onChange={setRiskFree}
          suffix="%"
        />
        <NumField
          label={PORTFOLIO_INPUTS.maxWeight.label}
          info={PORTFOLIO_INPUTS.maxWeight.info}
          value={maxWeight}
          onChange={setMaxWeight}
          suffix="%"
        />
        {objective === "mean_variance" && (
          <NumField
            label={PORTFOLIO_INPUTS.riskAversion.label}
            info={PORTFOLIO_INPUTS.riskAversion.info}
            value={riskAversion}
            onChange={setRiskAversion}
            suffix="γ"
          />
        )}
      </div>

      <label className="flex items-center gap-2 text-xs text-zinc-700">
        <input
          type="checkbox"
          checked={shrinkCovariance}
          onChange={(e) => setShrinkCovariance(e.target.checked)}
          className="h-3.5 w-3.5 rounded border-zinc-300"
        />
        <span>{PORTFOLIO_INPUTS.shrinkCovariance.label}</span>
        <span className="text-zinc-400">
          (Ledoit-Wolf shrinkage — reduces over-fitting)
        </span>
      </label>

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:bg-zinc-400"
      >
        {loading ? "Optimising…" : "Optimise + verify"}
      </button>
    </form>
  );
}

function NumField({
  label,
  value,
  onChange,
  suffix,
  info,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  suffix?: string;
  info?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center text-xs font-medium text-zinc-600">
        <label>{label}</label>
        {info && <InfoTooltip body={info} />}
      </div>
      <div className="relative">
        <input
          type="number"
          step="any"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 pr-8 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
          required
        />
        {suffix && (
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-zinc-500">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}
