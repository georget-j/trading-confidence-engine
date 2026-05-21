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

interface Props {
  spot: number;
  strike: number;
  premium: number;
  optionType: OptionType;
}

/** Classic hockey-stick payoff diagram at expiry.
 *  P/L = max(0, S - K) - premium  (call)
 *  P/L = max(0, K - S) - premium  (put) */
export function PayoffChart({ spot, strike, premium, optionType }: Props) {
  const breakeven = optionType === "call" ? strike + premium : strike - premium;

  // x-axis range — centred on spot, ±40% so both sides of breakeven are visible.
  const xMin = Math.max(0, Math.min(spot, strike, breakeven) * 0.6);
  const xMax = Math.max(spot, strike, breakeven) * 1.4;
  const N = 80;
  const step = (xMax - xMin) / (N - 1);
  const data = Array.from({ length: N }, (_, i) => {
    const s = xMin + i * step;
    const intrinsic =
      optionType === "call" ? Math.max(s - strike, 0) : Math.max(strike - s, 0);
    const pnl = intrinsic - premium;
    return { s, pnl, pnlPos: Math.max(pnl, 0), pnlNeg: Math.min(pnl, 0) };
  });

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
        </ComposedChart>
      </ResponsiveContainer>
      <p className="text-[11px] leading-snug text-zinc-600">
        Profit/loss at expiry as a function of the underlying price. You profit{" "}
        {optionType === "call" ? (
          <>
            <span className="font-semibold">above ${breakeven.toFixed(2)}</span>
          </>
        ) : (
          <>
            <span className="font-semibold">below ${breakeven.toFixed(2)}</span>
          </>
        )}
        ; max loss is the premium paid ($
        {premium.toFixed(2)}).
      </p>
    </div>
  );
}
