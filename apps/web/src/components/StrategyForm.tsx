"use client";

import { useState } from "react";
import { OPTIONS_INPUTS, STRATEGY_INPUTS } from "@/lib/copy";
import type {
  OptionsStrategyRequest,
  OptionType,
  StrategyLeg,
} from "@/lib/types";
import { InfoTooltip } from "./InfoTooltip";

// Per-leg input fields stay as strings while the user types — converted to
// numbers only at submit. Mirrors the single-leg PricingForm pattern.
interface LegState {
  optionType: OptionType;
  strike: string;
  quantity: string;
  days: string;
  vol: string;
}

interface FormState {
  spot: string;
  rate: string;
  div: string;
  legs: LegState[];
}

// ---- Presets --------------------------------------------------------------

type PresetId =
  | "custom"
  | "call_vertical"
  | "put_vertical"
  | "iron_condor"
  | "calendar"
  | "long_straddle"
  | "long_strangle";

interface PresetDef {
  id: PresetId;
  label: string;
  description: string;
  /** Builds the leg list for this preset given the underlying spot.
   *  Returns null for `custom` (which means "leave legs as they are"). */
  build: (spot: number) => LegState[] | null;
}

const DEFAULT_DAYS = "30";
const DEFAULT_VOL = "18";

function leg(
  type: OptionType,
  strike: number,
  qty: number,
  days: string = DEFAULT_DAYS,
  vol: string = DEFAULT_VOL,
): LegState {
  return {
    optionType: type,
    strike: strike.toFixed(2),
    quantity: qty.toString(),
    days,
    vol,
  };
}

const PRESETS: PresetDef[] = [
  {
    id: "custom",
    label: "Custom",
    description:
      "Build legs manually. Switching to another preset replaces all legs.",
    build: () => null,
  },
  {
    id: "call_vertical",
    label: "Call vertical (debit, bullish)",
    description:
      "Long ATM call + short OTM call. Caps profit but reduces the premium you pay. Bullish bias.",
    build: (spot) => [leg("call", spot, 1), leg("call", spot * 1.05, -1)],
  },
  {
    id: "put_vertical",
    label: "Put vertical (debit, bearish)",
    description:
      "Long ATM put + short OTM put. Caps profit but cheapens the bet. Bearish bias.",
    build: (spot) => [leg("put", spot, 1), leg("put", spot * 0.95, -1)],
  },
  {
    id: "iron_condor",
    label: "Iron condor (credit, neutral)",
    description:
      "Short put + long farther-OTM put, short call + long farther-OTM call. Collect premium when the underlying stays in a range.",
    build: (spot) => [
      leg("put", spot * 0.95, -1),
      leg("put", spot * 0.9, 1),
      leg("call", spot * 1.05, -1),
      leg("call", spot * 1.1, 1),
    ],
  },
  {
    id: "calendar",
    label: "Calendar (long vol, neutral)",
    description:
      "Short near-term ATM call + long far-term ATM call (same strike, different expiries). Benefits from time decay differential.",
    build: (spot) => [leg("call", spot, -1, "30"), leg("call", spot, 1, "90")],
  },
  {
    id: "long_straddle",
    label: "Long straddle (long vol)",
    description:
      "Long ATM call + long ATM put. Profits from a big move in either direction. Expensive — needs vol to expand.",
    build: (spot) => [leg("call", spot, 1), leg("put", spot, 1)],
  },
  {
    id: "long_strangle",
    label: "Long strangle (long vol, cheaper)",
    description:
      "Long OTM call + long OTM put. Cheaper than a straddle but needs a bigger move to break even.",
    build: (spot) => [leg("call", spot * 1.05, 1), leg("put", spot * 0.95, 1)],
  },
];

// Default = long call vertical on SPY 450 / 472.5, 30 days, 18% IV.
const DEFAULT_FORM: FormState = {
  spot: "450",
  rate: "5",
  div: "1.3",
  legs: PRESETS[1].build(450)!, // call vertical
};

const MAX_LEGS = 4;
const MIN_LEGS = 2;

interface Props {
  onSubmit: (req: OptionsStrategyRequest) => void;
  loading: boolean;
}

export function StrategyForm({ onSubmit, loading }: Props) {
  const [state, setState] = useState<FormState>(DEFAULT_FORM);
  // Tracks which preset the current legs match. Any manual edit flips this
  // back to "custom" so the dropdown reflects reality, not intent.
  const [presetId, setPresetId] = useState<PresetId>("call_vertical");

  function setShared<K extends keyof Omit<FormState, "legs">>(
    k: K,
    v: FormState[K],
  ) {
    setState({ ...state, [k]: v });
  }

  function setLeg<K extends keyof LegState>(idx: number, k: K, v: LegState[K]) {
    const next = state.legs.map((l, i) => (i === idx ? { ...l, [k]: v } : l));
    setState({ ...state, legs: next });
    setPresetId("custom");
  }

  function applyPreset(id: PresetId) {
    setPresetId(id);
    const preset = PRESETS.find((p) => p.id === id);
    if (!preset) return;
    const legs = preset.build(parseFloat(state.spot) || 450);
    if (legs === null) return; // "custom" is a no-op
    setState({ ...state, legs });
  }

  function addLeg() {
    if (state.legs.length >= MAX_LEGS) return;
    // New leg defaults to a long call ATM 30d / same IV as leg 0.
    const ref = state.legs[0];
    setState({
      ...state,
      legs: [
        ...state.legs,
        {
          optionType: "call",
          strike: state.spot,
          quantity: "1",
          days: ref.days,
          vol: ref.vol,
        },
      ],
    });
    setPresetId("custom");
  }

  function removeLeg(idx: number) {
    if (state.legs.length <= MIN_LEGS) return;
    setState({ ...state, legs: state.legs.filter((_, i) => i !== idx) });
    setPresetId("custom");
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const legs: StrategyLeg[] = state.legs.map((l) => ({
      option_type: l.optionType,
      strike: parseFloat(l.strike),
      quantity: parseInt(l.quantity, 10),
      time_to_expiry_years: parseFloat(l.days) / 365,
      volatility: parseFloat(l.vol) / 100,
    }));
    onSubmit({
      spot: parseFloat(state.spot),
      risk_free_rate: parseFloat(state.rate) / 100,
      dividend_yield: parseFloat(state.div) / 100,
      legs,
    });
  }

  const canAdd = state.legs.length < MAX_LEGS;
  const canRemove = state.legs.length > MIN_LEGS;

  const activePreset = PRESETS.find((p) => p.id === presetId);

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Preset picker */}
      <div className="space-y-1">
        <div className="flex items-center text-xs font-medium text-zinc-600">
          <label htmlFor="strategy-preset">Preset</label>
          <InfoTooltip body="Pre-built leg templates for the most common strategies. Picking one replaces the legs below. Any manual edit flips you to Custom." />
        </div>
        <select
          id="strategy-preset"
          value={presetId}
          onChange={(e) => applyPreset(e.target.value as PresetId)}
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none transition focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
        >
          {PRESETS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
        {activePreset && activePreset.id !== "custom" && (
          <p className="text-[11px] leading-snug text-zinc-500">
            {activePreset.description}
          </p>
        )}
      </div>

      {/* Shared underlying parameters */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <SmallField
          label={OPTIONS_INPUTS.spot.label}
          info={OPTIONS_INPUTS.spot.info}
          value={state.spot}
          onChange={(v) => setShared("spot", v)}
          suffix="$"
        />
        <SmallField
          label={OPTIONS_INPUTS.rate.label}
          info={OPTIONS_INPUTS.rate.info}
          value={state.rate}
          onChange={(v) => setShared("rate", v)}
          suffix="%"
        />
        <SmallField
          label={OPTIONS_INPUTS.div.label}
          info={OPTIONS_INPUTS.div.info}
          value={state.div}
          onChange={(v) => setShared("div", v)}
          suffix="%"
        />
      </div>

      {/* Legs */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Legs ({state.legs.length})
          </div>
          {canAdd && (
            <button
              type="button"
              onClick={addLeg}
              className="text-xs font-medium text-zinc-700 hover:text-zinc-900"
            >
              + Add leg
            </button>
          )}
        </div>
        {state.legs.map((leg, idx) => (
          <LegRow
            key={idx}
            idx={idx}
            leg={leg}
            onChange={(k, v) => setLeg(idx, k, v)}
            onRemove={canRemove ? () => removeLeg(idx) : undefined}
          />
        ))}
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:bg-zinc-400"
      >
        {loading ? "Pricing…" : "Price + verify strategy"}
      </button>
    </form>
  );
}

function LegRow({
  idx,
  leg,
  onChange,
  onRemove,
}: {
  idx: number;
  leg: LegState;
  onChange: <K extends keyof LegState>(k: K, v: LegState[K]) => void;
  onRemove?: () => void;
}) {
  const isLong = parseFloat(leg.quantity || "0") > 0;
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50/50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-600">
          <span>Leg {idx + 1}</span>
          <span
            className={
              isLong
                ? "rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] text-emerald-800"
                : "rounded bg-rose-100 px-1.5 py-0.5 text-[10px] text-rose-800"
            }
          >
            {isLong ? "long" : "short"}
          </span>
        </div>
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="text-[11px] text-zinc-500 hover:text-rose-700"
          >
            Remove
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <div className="space-y-1">
          <div className="flex items-center text-[10px] text-zinc-600">
            <label>{STRATEGY_INPUTS.optionType.label}</label>
            <InfoTooltip body={STRATEGY_INPUTS.optionType.info} />
          </div>
          <div className="inline-flex w-full rounded-md border border-zinc-300 p-0.5">
            {(["call", "put"] as OptionType[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => onChange("optionType", t)}
                className={`flex-1 rounded px-1 py-1 text-xs font-medium capitalize transition ${
                  leg.optionType === t
                    ? "bg-zinc-900 text-white"
                    : "text-zinc-600 hover:bg-zinc-100"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <SmallField
          label={STRATEGY_INPUTS.strike.label}
          info={STRATEGY_INPUTS.strike.info}
          value={leg.strike}
          onChange={(v) => onChange("strike", v)}
          suffix="$"
        />
        <SmallField
          label={STRATEGY_INPUTS.quantity.label}
          info={STRATEGY_INPUTS.quantity.info}
          value={leg.quantity}
          onChange={(v) => onChange("quantity", v)}
          allowNegative
        />
        <SmallField
          label={STRATEGY_INPUTS.days.label}
          info={STRATEGY_INPUTS.days.info}
          value={leg.days}
          onChange={(v) => onChange("days", v)}
          suffix="d"
        />
        <SmallField
          label={STRATEGY_INPUTS.vol.label}
          info={STRATEGY_INPUTS.vol.info}
          value={leg.vol}
          onChange={(v) => onChange("vol", v)}
          suffix="%"
        />
      </div>
    </div>
  );
}

function SmallField({
  label,
  info,
  value,
  onChange,
  suffix,
  allowNegative,
}: {
  label: string;
  info?: string;
  value: string;
  onChange: (v: string) => void;
  suffix?: string;
  allowNegative?: boolean;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center text-[10px] text-zinc-600">
        <label>{label}</label>
        {info && <InfoTooltip body={info} />}
      </div>
      <div className="relative">
        <input
          type="number"
          step={allowNegative ? "1" : "any"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 pr-6 text-xs text-zinc-900 outline-none transition focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
          required
        />
        {suffix && (
          <span className="pointer-events-none absolute inset-y-0 right-2 flex items-center text-[10px] text-zinc-500">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}
