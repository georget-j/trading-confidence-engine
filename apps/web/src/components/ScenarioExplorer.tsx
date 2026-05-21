"use client";

import { useMemo, useState } from "react";
import {
  Area,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { blackScholes } from "@/lib/black_scholes";
import type { OptionsPriceResult, OptionsPricingRequest } from "@/lib/types";
import { InfoTooltip } from "./InfoTooltip";

interface Props {
  /** The original (server-verified) request — the explorer starts here and
   *  the sliders perturb FROM this baseline. */
  baseRequest: OptionsPricingRequest;
  /** The server-computed primary result for cross-check. If the client BSM
   *  diverges from this by more than `CROSS_CHECK_TOL`, the explorer hides
   *  itself rather than mislead. */
  baseResult: OptionsPriceResult;
}

const CROSS_CHECK_TOL = 1e-2;

/** Interactive what-if explorer. Pure client-side BSM, sub-100ms slider
 *  feedback. The original verified result stays visible above; this is
 *  clearly labelled "scenario", not "verified". */
export function ScenarioExplorer({ baseRequest, baseResult }: Props) {
  // Cross-check the client BSM against the server on mount.
  const checkResult = useMemo(() => blackScholes(baseRequest), [baseRequest]);
  const priceMismatch =
    Math.abs(checkResult.price - baseResult.price) > CROSS_CHECK_TOL;

  // Slider state — start at the base inputs. The user perturbs from there.
  const [spotMult, setSpotMult] = useState(1.0); // 0.7 .. 1.3
  const [volMult, setVolMult] = useState(1.0); // 0.5 .. 2.0
  const [daysMult, setDaysMult] = useState(1.0); // 0.05 .. 1.0 of original

  const scenario = useMemo(() => {
    return {
      ...baseRequest,
      spot: baseRequest.spot * spotMult,
      volatility: baseRequest.volatility * volMult,
      time_to_expiry_years: baseRequest.time_to_expiry_years * daysMult,
    };
  }, [baseRequest, spotMult, volMult, daysMult]);

  const live = useMemo(() => blackScholes(scenario), [scenario]);

  // Payoff curve for the scenario — at the (scenario) expiry, P/L vs spot.
  // We keep the strike fixed (you can't slide it — that's a different option).
  const payoffData = useMemo(() => {
    const xMin = baseRequest.spot * 0.6;
    const xMax = baseRequest.spot * 1.4;
    const N = 60;
    const step = (xMax - xMin) / (N - 1);
    return Array.from({ length: N }, (_, i) => {
      const s = xMin + i * step;
      const intrinsic =
        baseRequest.option_type === "call"
          ? Math.max(s - baseRequest.strike, 0)
          : Math.max(baseRequest.strike - s, 0);
      const pnl = intrinsic - live.price;
      return { s, pnl, pnlPos: Math.max(pnl, 0), pnlNeg: Math.min(pnl, 0) };
    });
  }, [baseRequest, live.price]);

  if (priceMismatch) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        <div className="font-semibold">Scenario explorer unavailable</div>
        <p className="mt-1 text-amber-800">
          Client-side Black-Scholes diverges from the verified server price
          (client {checkResult.price.toFixed(4)} vs server{" "}
          {baseResult.price.toFixed(4)}). Refusing to show what-if numbers that
          wouldn&apos;t match the engine&apos;s verification stack.
        </p>
      </div>
    );
  }

  const baseDays = Math.round(baseRequest.time_to_expiry_years * 365);
  const scenDays = Math.round(scenario.time_to_expiry_years * 365);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center font-semibold text-zinc-900">
          <span>Scenario explorer</span>
          <InfoTooltip body="What-if calculator. Slide spot, vol, or days-to-expiry to see how the option's price and Greeks would react. Numbers here are client-side approximations — the engine's verified result stays above this panel." />
        </div>
        <button
          type="button"
          onClick={() => {
            setSpotMult(1.0);
            setVolMult(1.0);
            setDaysMult(1.0);
          }}
          className="text-zinc-500 hover:text-zinc-900"
        >
          Reset
        </button>
      </div>

      <div className="space-y-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3">
        <SliderRow
          label="Spot"
          baseValue={`$${baseRequest.spot.toFixed(2)}`}
          liveValue={`$${scenario.spot.toFixed(2)}`}
          delta={`${spotMult >= 1 ? "+" : ""}${((spotMult - 1) * 100).toFixed(1)}%`}
          min={0.7}
          max={1.3}
          step={0.005}
          value={spotMult}
          onChange={setSpotMult}
        />
        <SliderRow
          label="IV"
          baseValue={`${(baseRequest.volatility * 100).toFixed(1)}%`}
          liveValue={`${(scenario.volatility * 100).toFixed(1)}%`}
          delta={`${volMult >= 1 ? "+" : ""}${((volMult - 1) * 100).toFixed(0)}%`}
          min={0.3}
          max={2.5}
          step={0.05}
          value={volMult}
          onChange={setVolMult}
        />
        <SliderRow
          label="Days to expiry"
          baseValue={`${baseDays}d`}
          liveValue={`${scenDays}d`}
          delta={`${daysMult >= 1 ? "+" : ""}${((daysMult - 1) * 100).toFixed(0)}%`}
          min={0.05}
          max={1.0}
          step={0.01}
          value={daysMult}
          onChange={setDaysMult}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-zinc-200 p-3">
          <div className="text-[10px] uppercase tracking-wide text-zinc-500">
            Scenario price
          </div>
          <div className="mt-0.5 font-mono text-2xl font-semibold text-zinc-900">
            ${live.price.toFixed(4)}
          </div>
          <div
            className={`mt-0.5 text-xs ${
              live.price >= baseResult.price
                ? "text-emerald-700"
                : "text-rose-700"
            }`}
          >
            {live.price >= baseResult.price ? "+" : ""}$
            {(live.price - baseResult.price).toFixed(4)} vs verified
          </div>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          <MiniStat label="Δ" value={live.delta} digits={4} />
          <MiniStat label="Γ" value={live.gamma} digits={5} />
          <MiniStat label="ν" value={live.vega} digits={4} />
          <MiniStat label="Θ" value={live.theta} digits={4} />
        </div>
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart
          data={payoffData}
          margin={{ top: 5, right: 12, left: 0, bottom: 5 }}
        >
          <XAxis
            dataKey="s"
            type="number"
            domain={[
              Math.round(baseRequest.spot * 0.6),
              Math.round(baseRequest.spot * 1.4),
            ]}
            tickFormatter={(v) =>
              typeof v === "number" ? `$${v.toFixed(0)}` : String(v)
            }
            tick={{ fontSize: 9, fill: "#71717a" }}
            stroke="#d4d4d8"
          />
          <YAxis
            tickFormatter={(v) =>
              typeof v === "number" ? `$${v.toFixed(0)}` : String(v)
            }
            tick={{ fontSize: 9, fill: "#71717a" }}
            stroke="#d4d4d8"
            width={42}
          />
          <Tooltip
            contentStyle={{
              fontSize: 11,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid #d4d4d8",
            }}
            labelFormatter={(label) =>
              typeof label === "number"
                ? `Underlying $${label.toFixed(2)}`
                : String(label)
            }
            formatter={(value, name) => {
              if (name === "pnl" && typeof value === "number") {
                return [`$${value.toFixed(2)}`, "P/L"];
              }
              return ["", ""];
            }}
          />
          <Area
            dataKey="pnlPos"
            stroke="none"
            fill="#10b981"
            fillOpacity={0.25}
            isAnimationActive={false}
          />
          <Area
            dataKey="pnlNeg"
            stroke="none"
            fill="#ef4444"
            fillOpacity={0.25}
            isAnimationActive={false}
          />
          <Line
            type="linear"
            dataKey="pnl"
            stroke="#18181b"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          <ReferenceLine y={0} stroke="#a1a1aa" strokeDasharray="2 2" />
          <ReferenceLine
            x={scenario.spot}
            stroke="#0ea5e9"
            strokeDasharray="3 3"
          />
        </ComposedChart>
      </ResponsiveContainer>

      <p className="text-[11px] leading-snug text-zinc-600">
        Live payoff at expiry under the scenario. Drag sliders to explore. The
        blue dashed line is the scenario&apos;s spot price; max loss is the
        (scenario) premium paid.
      </p>
    </div>
  );
}

function SliderRow({
  label,
  baseValue,
  liveValue,
  delta,
  min,
  max,
  step,
  value,
  onChange,
}: {
  label: string;
  baseValue: string;
  liveValue: string;
  delta: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-medium text-zinc-700">{label}</span>
        <span className="font-mono text-zinc-500">
          {baseValue} → <span className="text-zinc-900">{liveValue}</span>{" "}
          <span className="text-zinc-400">({delta})</span>
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="mt-1 h-1 w-full cursor-pointer appearance-none rounded-full bg-zinc-200 accent-zinc-900"
      />
    </div>
  );
}

function MiniStat({
  label,
  value,
  digits,
}: {
  label: string;
  value: number;
  digits: number;
}) {
  return (
    <div className="rounded-md border border-zinc-200 px-2 py-1">
      <div className="text-[10px] text-zinc-500">{label}</div>
      <div className="font-mono text-xs text-zinc-900">
        {value.toFixed(digits)}
      </div>
    </div>
  );
}
