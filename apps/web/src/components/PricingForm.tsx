"use client";

import { OPTIONS_INPUTS } from "@/lib/copy";
import type { OptionsPricingRequest, OptionType } from "@/lib/types";
import { InfoTooltip } from "./InfoTooltip";

export interface PricingFormState {
  spot: string;
  strike: string;
  days: string;
  vol: string;
  rate: string;
  div: string;
  optionType: OptionType;
}

export const DEFAULT_FORM_STATE: PricingFormState = {
  spot: "450",
  strike: "450",
  days: "30",
  vol: "18",
  rate: "5",
  div: "1.3",
  optionType: "call",
};

interface Props {
  state: PricingFormState;
  onChange: (next: PricingFormState) => void;
  onSubmit: (req: OptionsPricingRequest) => void;
  loading: boolean;
  highlight?: boolean;
}

export function PricingForm({
  state,
  onChange,
  onSubmit,
  loading,
  highlight,
}: Props) {
  const set = <K extends keyof PricingFormState>(
    k: K,
    v: PricingFormState[K],
  ) => onChange({ ...state, [k]: v });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      spot: parseFloat(state.spot),
      strike: parseFloat(state.strike),
      time_to_expiry_years: parseFloat(state.days) / 365,
      volatility: parseFloat(state.vol) / 100,
      risk_free_rate: parseFloat(state.rate) / 100,
      dividend_yield: parseFloat(state.div) / 100,
      option_type: state.optionType,
      style: "european",
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={`space-y-4 ${
        highlight
          ? "rounded-lg ring-2 ring-emerald-300 ring-offset-2 transition"
          : ""
      }`}
    >
      <div className="grid grid-cols-2 gap-4">
        <Field
          label={OPTIONS_INPUTS.spot.label}
          info={OPTIONS_INPUTS.spot.info}
          value={state.spot}
          onChange={(v) => set("spot", v)}
          suffix="$"
        />
        <Field
          label={OPTIONS_INPUTS.strike.label}
          info={OPTIONS_INPUTS.strike.info}
          value={state.strike}
          onChange={(v) => set("strike", v)}
          suffix="$"
        />
        <Field
          label={OPTIONS_INPUTS.days.label}
          info={OPTIONS_INPUTS.days.info}
          value={state.days}
          onChange={(v) => set("days", v)}
          suffix="d"
        />
        <Field
          label={OPTIONS_INPUTS.vol.label}
          info={OPTIONS_INPUTS.vol.info}
          value={state.vol}
          onChange={(v) => set("vol", v)}
          suffix="%"
        />
        <Field
          label={OPTIONS_INPUTS.rate.label}
          info={OPTIONS_INPUTS.rate.info}
          value={state.rate}
          onChange={(v) => set("rate", v)}
          suffix="%"
        />
        <Field
          label={OPTIONS_INPUTS.div.label}
          info={OPTIONS_INPUTS.div.info}
          value={state.div}
          onChange={(v) => set("div", v)}
          suffix="%"
        />
      </div>

      <div className="space-y-1">
        <div className="flex items-center text-xs font-medium text-zinc-600">
          <label>{OPTIONS_INPUTS.optionType.label}</label>
          <InfoTooltip body={OPTIONS_INPUTS.optionType.info} />
        </div>
        <div className="inline-flex rounded-lg border border-zinc-300 p-0.5">
          {(["call", "put"] as OptionType[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => set("optionType", t)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium capitalize transition ${
                state.optionType === t
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

export function formStateFromRequest(
  req: OptionsPricingRequest,
): PricingFormState {
  return {
    spot: String(req.spot),
    strike: String(req.strike),
    days: String(Math.round(req.time_to_expiry_years * 365)),
    vol: (req.volatility * 100).toFixed(2),
    rate: (req.risk_free_rate * 100).toFixed(2),
    div: (req.dividend_yield * 100).toFixed(2),
    optionType: req.option_type,
  };
}
