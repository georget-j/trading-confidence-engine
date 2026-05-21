"use client";

import { useState } from "react";
import type { OptionsPricingRequest, OptionType } from "@/lib/types";

interface Props {
  onSubmit: (req: OptionsPricingRequest) => void;
  loading: boolean;
}

export function PricingForm({ onSubmit, loading }: Props) {
  const [spot, setSpot] = useState("450");
  const [strike, setStrike] = useState("450");
  const [days, setDays] = useState("30");
  const [vol, setVol] = useState("18");
  const [rate, setRate] = useState("5");
  const [div, setDiv] = useState("1.3");
  const [optionType, setOptionType] = useState<OptionType>("call");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      spot: parseFloat(spot),
      strike: parseFloat(strike),
      time_to_expiry_years: parseFloat(days) / 365,
      volatility: parseFloat(vol) / 100,
      risk_free_rate: parseFloat(rate) / 100,
      dividend_yield: parseFloat(div) / 100,
      option_type: optionType,
      style: "european",
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field
          label="Underlying spot"
          value={spot}
          onChange={setSpot}
          suffix="$"
        />
        <Field label="Strike" value={strike} onChange={setStrike} suffix="$" />
        <Field
          label="Days to expiry"
          value={days}
          onChange={setDays}
          suffix="d"
        />
        <Field label="Implied vol" value={vol} onChange={setVol} suffix="%" />
        <Field
          label="Risk-free rate"
          value={rate}
          onChange={setRate}
          suffix="%"
        />
        <Field
          label="Dividend yield"
          value={div}
          onChange={setDiv}
          suffix="%"
        />
      </div>

      <div className="space-y-1">
        <label className="text-xs font-medium text-zinc-600">Option type</label>
        <div className="inline-flex rounded-lg border border-zinc-300 p-0.5">
          {(["call", "put"] as OptionType[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setOptionType(t)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium capitalize transition ${
                optionType === t
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-600 hover:bg-zinc-100"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:bg-zinc-400"
      >
        {loading ? "Pricing…" : "Price + verify"}
      </button>
    </form>
  );
}

function Field({
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
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 pr-8 text-sm text-zinc-900 outline-none transition focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
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
