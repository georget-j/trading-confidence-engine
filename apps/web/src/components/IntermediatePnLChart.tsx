"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { blackScholes, type OptionType } from "@/lib/black_scholes";

/** A leg priced at t=0, with all fields needed to re-price it at any
 *  future date via client-side BSM. `premium` is the cost basis (the price
 *  the server computed at t=0); `quantity` is signed. */
export interface IntermediateLeg {
  strike: number;
  premium: number;
  optionType: OptionType;
  quantity: number;
  time_to_expiry_years: number;
  volatility: number;
}

interface Props {
  spot: number;
  riskFreeRate: number;
  dividendYield: number;
  legs: IntermediateLeg[];
}

// Intrinsic value at expiry — used when a leg's remaining time hits zero.
function intrinsic(leg: IntermediateLeg, s: number): number {
  return leg.optionType === "call"
    ? Math.max(s - leg.strike, 0)
    : Math.max(leg.strike - s, 0);
}

// Cost basis (what we paid net) for all legs combined.
function netCostBasis(legs: IntermediateLeg[]): number {
  return legs.reduce((acc, l) => acc + l.quantity * l.premium, 0);
}

// Current portfolio value at a given (spot, days_elapsed). For each leg,
// either BSM-reprice with the leg's remaining T, or fall back to intrinsic
// when the leg has expired.
function portfolioValue(
  legs: IntermediateLeg[],
  spot: number,
  daysElapsed: number,
  r: number,
  q: number,
): number {
  let value = 0;
  for (const leg of legs) {
    const remaining = leg.time_to_expiry_years - daysElapsed / 365;
    if (remaining <= 1e-6) {
      value += leg.quantity * intrinsic(leg, spot);
    } else {
      const bs = blackScholes({
        spot,
        strike: leg.strike,
        time_to_expiry_years: remaining,
        volatility: leg.volatility,
        risk_free_rate: r,
        dividend_yield: q,
        option_type: leg.optionType,
      });
      value += leg.quantity * bs.price;
    }
  }
  return value;
}

// 4 time slices keyed by the longest leg's expiry. Colors ramp from light
// (now) to dark (at expiry) so the eye picks up the time direction.
interface Slice {
  daysElapsed: number;
  label: string;
  color: string;
  dataKey: string;
}

export function IntermediatePnLChart({
  spot,
  riskFreeRate,
  dividendYield,
  legs,
}: Props) {
  const maxExpiryDays = Math.max(
    ...legs.map((l) => Math.round(l.time_to_expiry_years * 365)),
  );

  const slices: Slice[] = [
    {
      daysElapsed: 0,
      label: "Now",
      color: "#93c5fd",
      dataKey: "pnlNow",
    },
    {
      daysElapsed: Math.round(maxExpiryDays / 3),
      label: `T+${Math.round(maxExpiryDays / 3)}d`,
      color: "#3b82f6",
      dataKey: "pnlT1",
    },
    {
      daysElapsed: Math.round((2 * maxExpiryDays) / 3),
      label: `T+${Math.round((2 * maxExpiryDays) / 3)}d`,
      color: "#1e40af",
      dataKey: "pnlT2",
    },
    {
      daysElapsed: maxExpiryDays,
      label: "At expiry",
      color: "#18181b",
      dataKey: "pnlExpiry",
    },
  ];

  const cost = netCostBasis(legs);
  const strikes = legs.map((l) => l.strike);
  const anchors = [spot, ...strikes];
  const xMin = Math.max(0, Math.min(...anchors) * 0.7);
  const xMax = Math.max(...anchors) * 1.3;
  const N = 60;
  const step = (xMax - xMin) / (N - 1);

  const data = Array.from({ length: N }, (_, i) => {
    const s = xMin + i * step;
    const row: { s: number } & Record<string, number> = { s };
    for (const slice of slices) {
      row[slice.dataKey] =
        portfolioValue(
          legs,
          s,
          slice.daysElapsed,
          riskFreeRate,
          dividendYield,
        ) - cost;
    }
    return row;
  });

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart
          data={data}
          margin={{ top: 8, right: 16, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="2 4" stroke="#e4e4e7" />
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
            width={48}
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
              const slice = slices.find((s) => s.dataKey === name);
              if (typeof value === "number" && slice) {
                return [`$${value.toFixed(2)}`, slice.label];
              }
              return [String(value ?? ""), String(name ?? "")];
            }}
          />
          <Legend
            verticalAlign="top"
            height={24}
            iconSize={10}
            wrapperStyle={{ fontSize: 11, color: "#52525b" }}
            formatter={(value) => {
              const slice = slices.find((s) => s.dataKey === value);
              return slice ? slice.label : value;
            }}
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
          {slices.map((slice) => (
            <Line
              key={slice.dataKey}
              type="monotone"
              dataKey={slice.dataKey}
              stroke={slice.color}
              strokeWidth={slice.dataKey === "pnlExpiry" ? 2 : 1.5}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <p className="text-[11px] leading-snug text-zinc-600">
        Estimated P/L at four points in time, assuming vol and rates stay
        constant. The &ldquo;Now&rdquo; curve passes through ($0, current spot)
        by construction; the &ldquo;At expiry&rdquo; curve is the hockey stick.
        Client-side BSM — the verified server result above is the source of
        truth.
      </p>
    </div>
  );
}
