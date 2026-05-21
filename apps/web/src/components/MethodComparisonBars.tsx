"use client";

import {
  Bar,
  BarChart,
  Cell,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CalculatorResult, VaRPayload } from "@/lib/types";

interface Props {
  results: CalculatorResult[];
}

const TIGHT_REL = 0.05; // 5% — matches backend VAR_TIGHT_REL_TOL
const WIDE_REL = 0.2; // 20% — matches backend VAR_WIDE_REL_TOL

const FMT_USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

/** Three-method VaR comparison: horizontal bars + shaded tight/wide bands.
 *  Makes 'verified' vs 'partially_verified' visually obvious. */
export function MethodComparisonBars({ results }: Props) {
  const rows = results
    .filter((r) => r.succeeded && r.payload.kind === "var")
    .map((r) => ({
      method: friendlyName(r.calculator_id),
      var: (r.payload as VaRPayload).var_loss,
    }));

  if (rows.length === 0) {
    return null;
  }

  const median = rows.map((r) => r.var).sort((a, b) => a - b)[
    Math.floor(rows.length / 2)
  ];
  const tightMin = median * (1 - TIGHT_REL);
  const tightMax = median * (1 + TIGHT_REL);
  const wideMin = median * (1 - WIDE_REL);
  const wideMax = median * (1 + WIDE_REL);

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={140}>
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 5, right: 16, left: 0, bottom: 5 }}
        >
          <XAxis
            type="number"
            tickFormatter={(v: number) => FMT_USD.format(v)}
            tick={{ fontSize: 10, fill: "#71717a" }}
            stroke="#d4d4d8"
          />
          <YAxis
            type="category"
            dataKey="method"
            tick={{ fontSize: 11, fill: "#3f3f46" }}
            stroke="#d4d4d8"
            width={110}
          />
          <Tooltip
            contentStyle={{
              fontSize: 11,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid #d4d4d8",
            }}
            formatter={(value) => [
              typeof value === "number" ? FMT_USD.format(value) : String(value),
              "VaR",
            ]}
          />
          {/* Wide band (20%) — pale amber */}
          <ReferenceArea
            x1={wideMin}
            x2={wideMax}
            fill="#fef3c7"
            fillOpacity={0.45}
          />
          {/* Tight band (5%) — pale emerald, drawn on top of wide */}
          <ReferenceArea
            x1={tightMin}
            x2={tightMax}
            fill="#d1fae5"
            fillOpacity={0.7}
          />
          <Bar dataKey="var" isAnimationActive={false} barSize={18}>
            {rows.map((r, i) => (
              <Cell
                key={i}
                fill={
                  r.var >= tightMin && r.var <= tightMax
                    ? "#059669"
                    : r.var >= wideMin && r.var <= wideMax
                      ? "#d97706"
                      : "#dc2626"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-3 text-[10px] text-zinc-500">
        <Legend color="bg-emerald-100" label="Tight band (≤5%)" />
        <Legend color="bg-amber-100" label="Wide band (≤20%)" />
        <Legend color="bg-rose-100" label="Outside tolerance" />
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`inline-block h-2 w-3 rounded-sm ${color}`} />
      {label}
    </span>
  );
}

function friendlyName(calculatorId: string): string {
  switch (calculatorId) {
    case "historical_var":
      return "Historical";
    case "parametric_var":
      return "Parametric";
    case "monte_carlo_var":
      return "Monte Carlo";
    default:
      return calculatorId;
  }
}
