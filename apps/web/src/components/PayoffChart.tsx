"use client";

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
import type { OptionType } from "@/lib/types";

/** One leg of a (possibly multi-leg) options position. `quantity` is signed:
 *  positive = long, negative = short. Premium is per-contract (positive). */
export interface PayoffLeg {
  strike: number;
  premium: number;
  optionType: OptionType;
  quantity: number;
}

interface Props {
  spot: number;
  /** Single-leg props — used when `legs` is not supplied. Existing callers
   *  pass these and get the classic hockey-stick payoff. */
  strike?: number;
  premium?: number;
  optionType?: OptionType;
  /** Optional list of legs for multi-leg strategies. When provided, overrides
   *  the single-leg props and renders aggregate P/L at expiry. */
  legs?: PayoffLeg[];
}

function legPnL(leg: PayoffLeg, s: number): number {
  const intrinsic =
    leg.optionType === "call"
      ? Math.max(s - leg.strike, 0)
      : Math.max(leg.strike - s, 0);
  return leg.quantity * (intrinsic - leg.premium);
}

/** Payoff diagram at expiry. Single-leg mode produces the classic hockey
 *  stick with breakeven label; multi-leg mode renders aggregate P/L (no
 *  breakeven label — multi-leg payoffs can have multiple breakevens). */
export function PayoffChart(props: Props) {
  const { spot } = props;

  // Resolve to a unified leg list. Single-leg callers (current behaviour) get
  // bit-identical output to the previous implementation.
  const legs: PayoffLeg[] = props.legs ?? [
    {
      strike: props.strike ?? spot,
      premium: props.premium ?? 0,
      optionType: props.optionType ?? "call",
      quantity: 1,
    },
  ];
  const isSingleLeg = !props.legs && legs.length === 1;
  const singleLeg = isSingleLeg ? legs[0] : null;
  const breakeven =
    singleLeg !== null
      ? singleLeg.optionType === "call"
        ? singleLeg.strike + singleLeg.premium
        : singleLeg.strike - singleLeg.premium
      : null;

  // x-axis range — centred on spot, ±40%, also widened to include every
  // leg's strike and the (single-leg) breakeven so they're all visible.
  const anchors: number[] = [spot, ...legs.map((l) => l.strike)];
  if (breakeven !== null) anchors.push(breakeven);
  const xMin = Math.max(0, Math.min(...anchors) * 0.6);
  const xMax = Math.max(...anchors) * 1.4;
  const N = 80;
  const step = (xMax - xMin) / (N - 1);
  const data = Array.from({ length: N }, (_, i) => {
    const s = xMin + i * step;
    const pnl = legs.reduce((acc, leg) => acc + legPnL(leg, s), 0);
    return { s, pnl, pnlPos: Math.max(pnl, 0), pnlNeg: Math.min(pnl, 0) };
  });

  // Max loss for the caption — single-leg long is the premium paid; for
  // multi-leg or single-leg short we fall back to the chart's lowest P/L.
  const maxLoss = -Math.min(...data.map((d) => d.pnl));

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart
          data={data}
          margin={{ top: 8, right: 16, left: 0, bottom: 5 }}
        >
          <XAxis
            dataKey="s"
            type="number"
            domain={[xMin, xMax]}
            tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            tick={{ fontSize: 10, fill: "#71717a" }}
            stroke="#d4d4d8"
          />
          <YAxis
            tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            tick={{ fontSize: 10, fill: "#71717a" }}
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
            x={spot}
            stroke="#0ea5e9"
            strokeDasharray="3 3"
            label={{
              value: `spot $${spot.toFixed(0)}`,
              position: "insideTopLeft",
              fontSize: 10,
              fill: "#0ea5e9",
            }}
          />
          {breakeven !== null && (
            <ReferenceLine
              x={breakeven}
              stroke="#7c3aed"
              strokeDasharray="3 3"
              label={{
                value: `breakeven $${breakeven.toFixed(2)}`,
                position: "insideTopRight",
                fontSize: 10,
                fill: "#7c3aed",
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      <p className="text-[11px] leading-snug text-zinc-600">
        {singleLeg !== null && breakeven !== null ? (
          <>
            Profit/loss at expiry as a function of the underlying price. You
            profit{" "}
            {singleLeg.optionType === "call" ? (
              <span className="font-semibold">
                above ${breakeven.toFixed(2)}
              </span>
            ) : (
              <span className="font-semibold">
                below ${breakeven.toFixed(2)}
              </span>
            )}
            ; max loss is the premium paid (${singleLeg.premium.toFixed(2)}).
          </>
        ) : (
          <>
            Aggregate profit/loss at expiry across {legs.length} legs. Max loss
            in the plotted range is ${maxLoss.toFixed(2)}.
          </>
        )}
      </p>
    </div>
  );
}
