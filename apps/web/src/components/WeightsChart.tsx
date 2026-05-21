"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AssetWeight } from "@/lib/types";

interface Props {
  weights: AssetWeight[];
}

// Each entry shows weight vs risk contribution side-by-side. A retail user
// who sees risk_contribution much larger than weight learns immediately
// that the asset is dominating risk despite its modest allocation.
const COL_WEIGHT = "#0ea5e9"; // sky-500
const COL_RISK = "#f97316"; // orange-500

/** Horizontal bars: weight and risk contribution per asset. */
export function WeightsChart({ weights }: Props) {
  const rows = [...weights]
    .filter((w) => w.weight > 0.0001 || w.risk_contribution > 0.0001)
    .sort((a, b) => b.weight - a.weight)
    .map((w) => ({
      ticker: w.ticker,
      weightPct: w.weight * 100,
      riskPct: w.risk_contribution * 100,
    }));

  const height = Math.max(120, rows.length * 32);

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 5, right: 16, left: 0, bottom: 5 }}
        >
          <XAxis
            type="number"
            tickFormatter={(v) =>
              typeof v === "number" ? `${v.toFixed(0)}%` : String(v)
            }
            tick={{ fontSize: 10, fill: "#71717a" }}
            stroke="#d4d4d8"
          />
          <YAxis
            type="category"
            dataKey="ticker"
            tick={{ fontSize: 11, fill: "#3f3f46", fontFamily: "monospace" }}
            stroke="#d4d4d8"
            width={70}
          />
          <Tooltip
            contentStyle={{
              fontSize: 11,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid #d4d4d8",
            }}
            formatter={(value, name) => {
              if (typeof value !== "number") return ["", ""];
              const labelMap: Record<string, string> = {
                weightPct: "Weight",
                riskPct: "Risk contribution",
              };
              return [
                `${value.toFixed(2)}%`,
                labelMap[String(name)] ?? String(name),
              ];
            }}
          />
          <Bar dataKey="weightPct" isAnimationActive={false} barSize={10}>
            {rows.map((_, i) => (
              <Cell key={`w-${i}`} fill={COL_WEIGHT} />
            ))}
          </Bar>
          <Bar dataKey="riskPct" isAnimationActive={false} barSize={10}>
            {rows.map((_, i) => (
              <Cell key={`r-${i}`} fill={COL_RISK} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-3 text-[10px] text-zinc-500">
        <Legend color={COL_WEIGHT} label="Weight (capital)" />
        <Legend color={COL_RISK} label="Risk contribution (variance)" />
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-block h-2 w-3 rounded-sm"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}
