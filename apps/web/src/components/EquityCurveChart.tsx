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
  // For the chart we also surface position state as a 0/1 background flag,
  // and compute return-since-inception so the tooltip can show absolute and
  // relative P/L at the hovered day.
  const data = curve.map((p) => ({
    day: p.day_index,
    equity: p.equity,
    flatRegion: p.position < 0.5 ? p.equity : null,
    position: p.position,
    pnl: p.equity - initialCapital,
    returnPct:
      initialCapital > 0 ? (p.equity - initialCapital) / initialCapital : 0,
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
            cursor={{ stroke: "#a1a1aa", strokeDasharray: "2 4" }}
            content={({ active, payload, label }) => {
              if (
                !active ||
                !payload ||
                payload.length === 0 ||
                payload[0]?.payload === undefined
              ) {
                return null;
              }
              const row = payload[0].payload as (typeof data)[number];
              const up = row.pnl >= 0;
              const flat = row.position < 0.5;
              return (
                <div className="rounded-md border border-zinc-300 bg-white px-2.5 py-1.5 text-[11px] shadow-sm">
                  <div className="text-zinc-500">
                    Day {typeof label === "number" ? label : ""}
                  </div>
                  <div className="font-mono font-semibold text-zinc-900">
                    {FMT_USD.format(row.equity)}
                  </div>
                  <div
                    className={`font-mono ${
                      up ? "text-emerald-700" : "text-rose-700"
                    }`}
                  >
                    {up ? "+" : ""}
                    {FMT_USD.format(row.pnl)} ({up ? "+" : ""}
                    {(row.returnPct * 100).toFixed(2)}%)
                  </div>
                  <div className="text-zinc-500">
                    {flat ? "flat (out of market)" : "fully invested"}
                  </div>
                </div>
              );
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
