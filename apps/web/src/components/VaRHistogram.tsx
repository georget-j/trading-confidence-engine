"use client";

import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistogramBin } from "@/lib/types";

interface Props {
  bins: HistogramBin[];
  /** Daily return that defines the VaR threshold (negative). Bars at or below
   *  this are shaded as 'tail loss'. */
  varReturn: number;
  /** Mean daily return in the tail (used to mark the CVaR position). */
  cvarReturn: number;
  confidenceLevel: number;
}

const COL_TAIL = "#dc2626"; // rose-600 — losses worse than VaR
const COL_BODY = "#e4e4e7"; // zinc-200 — rest of the distribution

export function VaRHistogram({
  bins,
  varReturn,
  cvarReturn,
  confidenceLevel,
}: Props) {
  // Recharts wants one row per bar with the x-position as a number-like field.
  // We plot the mid-point of each bin on the x-axis so the bars line up with
  // their actual range.
  const data = bins.map((b) => {
    const mid = (b.bin_min + b.bin_max) / 2;
    const inTail = b.bin_max <= varReturn; // entire bin below VaR
    return {
      mid,
      pct: mid * 100,
      count: b.count,
      inTail,
    };
  });

  const tailPct = ((1 - confidenceLevel) * 100).toFixed(1);

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={180}>
        <BarChart
          data={data}
          margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        >
          <XAxis
            dataKey="pct"
            tickFormatter={(v: number) => `${v.toFixed(1)}%`}
            tick={{ fontSize: 10, fill: "#71717a" }}
            stroke="#d4d4d8"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#71717a" }}
            stroke="#d4d4d8"
            width={28}
          />
          <Tooltip
            contentStyle={{
              fontSize: 11,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid #d4d4d8",
            }}
            formatter={(value) => [
              typeof value === "number" ? `${value} days` : String(value),
              "count",
            ]}
            labelFormatter={(label) =>
              typeof label === "number"
                ? `${label.toFixed(2)}% daily return`
                : String(label)
            }
          />
          <ReferenceLine
            x={varReturn * 100}
            stroke="#dc2626"
            strokeDasharray="3 3"
            label={{
              value: `VaR ${(varReturn * 100).toFixed(2)}%`,
              position: "top",
              fontSize: 10,
              fill: "#dc2626",
            }}
          />
          <ReferenceLine
            x={cvarReturn * 100}
            stroke="#7f1d1d"
            strokeDasharray="2 2"
          />
          <Bar dataKey="count" isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.inTail ? COL_TAIL : COL_BODY} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-[11px] leading-snug text-zinc-600">
        Distribution of past daily returns. The red bars are the worst{" "}
        <span className="font-semibold">{tailPct}%</span> of days — losses in
        that range are what VaR is estimating.
      </p>
    </div>
  );
}
