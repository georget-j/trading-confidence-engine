"use client";

import { useState } from "react";
import type { VaRRequest } from "@/lib/types";

interface Props {
  onSubmit: (req: VaRRequest) => void;
  loading: boolean;
}

export function RiskForm({ onSubmit, loading }: Props) {
  const [ticker, setTicker] = useState("SPY");
  const [lookback, setLookback] = useState("504");
  const [portfolio, setPortfolio] = useState("10000");
  const [confidence, setConfidence] = useState("95");
  const [horizon, setHorizon] = useState("1");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      ticker: ticker.trim().toUpperCase(),
      lookback_days: parseInt(lookback, 10),
      portfolio_value: parseFloat(portfolio),
      confidence_level: parseFloat(confidence) / 100,
      horizon_days: parseInt(horizon, 10),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <label className="text-xs font-medium text-zinc-600">Ticker</label>
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="SPY, AAPL, TSLA…"
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm uppercase tracking-wide text-zinc-900 outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
          required
        />
        <p className="text-[10px] text-zinc-500">
          Fetched live via yfinance. First fetch can take a few seconds.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <NumField
          label="Portfolio value"
          value={portfolio}
          onChange={setPortfolio}
          suffix="$"
        />
        <NumField
          label="Lookback"
          value={lookback}
          onChange={setLookback}
          suffix="d"
        />
        <NumField
          label="Confidence"
          value={confidence}
          onChange={setConfidence}
          suffix="%"
        />
        <NumField
          label="Horizon"
          value={horizon}
          onChange={setHorizon}
          suffix="d"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:bg-zinc-400"
      >
        {loading ? "Computing VaR…" : "Compute VaR + verify"}
      </button>
    </form>
  );
}

function NumField({
  label,
  value,
  onChange,
  suffix,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  suffix?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-zinc-600">{label}</label>
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
