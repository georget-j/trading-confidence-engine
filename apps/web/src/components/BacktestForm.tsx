"use client";

import { useState } from "react";
import type { BacktestRequest, BacktestStrategy } from "@/lib/types";
import { InfoTooltip } from "./InfoTooltip";

interface Props {
  onSubmit: (req: BacktestRequest) => void;
  loading: boolean;
}

const STRATEGIES: { value: BacktestStrategy; label: string; info: string }[] = [
  {
    value: "buy_and_hold",
    label: "Buy & hold",
    info: "Always 100% invested in the underlying. The honest baseline that every active strategy should justify itself against.",
  },
  {
    value: "ma_crossover",
    label: "MA cross",
    info: "Long when the fast moving average is above the slow one, flat otherwise. Simple trend-following rule.",
  },
  {
    value: "momentum",
    label: "Momentum",
    info: "Long when the trailing-window cumulative return is positive. The most-cited 'anomaly' in academic finance.",
  },
];

export function BacktestForm({ onSubmit, loading }: Props) {
  const [ticker, setTicker] = useState("SPY");
  const [lookback, setLookback] = useState("504");
  const [strategy, setStrategy] = useState<BacktestStrategy>("ma_crossover");
  const [capital, setCapital] = useState("10000");
  const [slippage, setSlippage] = useState("5");
  const [maFast, setMaFast] = useState("20");
  const [maSlow, setMaSlow] = useState("50");
  const [momentumLookback, setMomentumLookback] = useState("60");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      ticker: ticker.trim().toUpperCase(),
      lookback_days: parseInt(lookback, 10),
      strategy,
      initial_capital: parseFloat(capital),
      slippage_bps: parseFloat(slippage),
      ma_fast: parseInt(maFast, 10),
      ma_slow: parseInt(maSlow, 10),
      momentum_lookback: parseInt(momentumLookback, 10),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <div className="flex items-center text-xs font-medium text-zinc-600">
          <label>Ticker</label>
          <InfoTooltip body="Single ticker to backtest. Daily prices fetched via yfinance." />
        </div>
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="SPY"
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm uppercase tracking-wide text-zinc-900 outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
          required
        />
      </div>

      <div className="space-y-1">
        <div className="flex items-center text-xs font-medium text-zinc-600">
          <label>Strategy</label>
        </div>
        <div className="inline-flex rounded-lg border border-zinc-300 p-0.5">
          {STRATEGIES.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setStrategy(s.value)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                strategy === s.value
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-600 hover:bg-zinc-100"
              }`}
              title={s.info}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <NumField
          label="Lookback"
          value={lookback}
          onChange={setLookback}
          suffix="d"
        />
        <NumField
          label="Capital"
          value={capital}
          onChange={setCapital}
          suffix="$"
        />
        <NumField
          label="Slippage"
          value={slippage}
          onChange={setSlippage}
          suffix="bp"
          info="Cost per position change in basis points. The result card shows how PnL changes with 0, 5, 10, 20, 50bp."
        />
      </div>

      {strategy === "ma_crossover" && (
        <div className="grid grid-cols-2 gap-3">
          <NumField
            label="Fast MA"
            value={maFast}
            onChange={setMaFast}
            suffix="d"
          />
          <NumField
            label="Slow MA"
            value={maSlow}
            onChange={setMaSlow}
            suffix="d"
          />
        </div>
      )}
      {strategy === "momentum" && (
        <NumField
          label="Lookback"
          value={momentumLookback}
          onChange={setMomentumLookback}
          suffix="d"
          info="Window for the trailing cumulative return signal."
        />
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:bg-zinc-400"
      >
        {loading ? "Running…" : "Backtest + verify"}
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
