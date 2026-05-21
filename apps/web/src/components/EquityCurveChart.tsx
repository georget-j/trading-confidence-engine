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
import type { EquityPoint } from "@/lib/types";

interface Props {
  curve: EquityPoint[];
  initialCapital: number;
}

const FMT_USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

/** Equity curve with shaded position state (long vs flat).
 *  Days when the strategy is flat get a lighter background so the user can
 *  see at a glance when the strategy was in the market. */
export function EquityCurveChart({ curve, initialCapital }: Props) {
  if (curve.length === 0) {
    return <div className="text-xs text-zinc-500">No equity curve.</div>;
  }
  // For the chart we also surface position state as a 0/1 background flag.
  const data = curve.map((p) => ({
    day: p.day_index,
    equity: p.equity,
    flatRegion: p.position < 0.5 ? p.equity : null,
  }));

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart
          data={data}
          margin={{ top: 8, right: 12, left: 0, bottom: 5 }}
        >
          <XAxis
            dataKey="day"
            tickFormatter={(v) => (typeof v === "number" ? `${v}d` : String(v))}
            tick={{ fontSize: 10, fill: "#71717a" }}
            stroke="#d4d4d8"
          />
          <YAxis
            tickFormatter={(v) =>
              typeof v === "number" ? FMT_USD.format(v) : String(v)
            }
            tick={{ fontSize: 10, fill: "#71717a" }}
            stroke="#d4d4d8"
            width={56}
            domain={["dataMin", "dataMax"]}
          />
          <Tooltip
            contentStyle={{
              fontSize: 11,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid #d4d4d8",
            }}
            labelFormatter={(label) =>
              typeof label === "number" ? `Day ${label}` : String(label)
            }
            formatter={(value, name) => {
              if (typeof value !== "number") return null;
              if (name === "equity") return [FMT_USD.format(value), "Equity"];
              return null;
            }}
          />
          <ReferenceLine
            y={initialCapital}
            stroke="#a1a1aa"
            strokeDasharray="2 2"
          />
          {/* Light grey band on days the strategy is flat. */}
          <Area
            dataKey="flatRegion"
            stroke="none"
            fill="#e4e4e7"
            fillOpacity={0.6}
            isAnimationActive={false}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="equity"
            stroke="#0ea5e9"
            strokeWidth={1.8}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="text-[11px] leading-snug text-zinc-600">
        Equity over the backtest window. Dashed line is starting capital.
        Grey-shaded bands are days the strategy was flat (out of the market).
      </p>
    </div>
  );
}
