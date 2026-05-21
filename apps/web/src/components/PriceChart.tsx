"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchPriceHistory, type PricePoint } from "@/lib/api";

interface Props {
  ticker: string;
  days?: number;
  /** How often (ms) to silently re-fetch. 0 to disable. Default 60s. */
  refreshIntervalMs?: number;
}

interface State {
  loading: boolean;
  points: PricePoint[];
  error: string | null;
  cached: boolean;
  lastFetched: Date | null;
}

const FMT_USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

/** Daily-close line chart with optional auto-refresh.
 *  Backend caches the upstream fetch for 60s, so a 30s UI refresh is cheap. */
export function PriceChart({
  ticker,
  days = 60,
  refreshIntervalMs = 60_000,
}: Props) {
  const [state, setState] = useState<State>({
    loading: true,
    points: [],
    error: null,
    cached: false,
    lastFetched: null,
  });

  const load = useCallback(async () => {
    try {
      const res = await fetchPriceHistory(ticker, days);
      setState({
        loading: false,
        points: res.points,
        error: null,
        cached: res.cached,
        lastFetched: new Date(),
      });
    } catch (e) {
      setState((s) => ({
        ...s,
        loading: false,
        error: e instanceof Error ? e.message : String(e),
      }));
    }
  }, [ticker, days]);

  useEffect(() => {
    setState((s) => ({ ...s, loading: true, error: null }));
    load();
    if (refreshIntervalMs > 0) {
      const id = window.setInterval(load, refreshIntervalMs);
      return () => window.clearInterval(id);
    }
    return undefined;
  }, [load, refreshIntervalMs]);

  if (state.loading && state.points.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-6 text-center text-xs text-zinc-500">
        Loading {ticker} prices…
      </div>
    );
  }

  if (state.error && state.points.length === 0) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
        Price data unavailable: {state.error}
      </div>
    );
  }

  const last = state.points[state.points.length - 1]?.close ?? 0;
  const first = state.points[0]?.close ?? last;
  const pctChange = first > 0 ? (last - first) / first : 0;
  const data = state.points.map((p) => ({
    date: p.date,
    close: p.close,
  }));

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <div>
          <span className="font-mono text-sm font-semibold text-zinc-900">
            {state.points.length > 0 ? FMT_USD.format(last) : "—"}
          </span>
          <span
            className={`ml-2 text-xs ${
              pctChange >= 0 ? "text-emerald-700" : "text-rose-700"
            }`}
          >
            {pctChange >= 0 ? "+" : ""}
            {(pctChange * 100).toFixed(2)}% over {days}d
          </span>
        </div>
        <div className="text-[10px] text-zinc-500">
          {state.lastFetched ? (
            <>
              Updated {state.lastFetched.toLocaleTimeString()}
              {state.cached ? " · cached" : ""}
            </>
          ) : null}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <AreaChart
          data={data}
          margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        >
          <defs>
            <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: "#71717a" }}
            stroke="#d4d4d8"
            interval="preserveStartEnd"
            tickFormatter={(v) =>
              typeof v === "string" ? v.slice(5) : String(v)
            }
          />
          <YAxis
            domain={["dataMin", "dataMax"]}
            tickFormatter={(v) =>
              typeof v === "number" ? FMT_USD.format(v) : String(v)
            }
            tick={{ fontSize: 9, fill: "#71717a" }}
            stroke="#d4d4d8"
            width={56}
          />
          <Tooltip
            contentStyle={{
              fontSize: 11,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid #d4d4d8",
            }}
            labelFormatter={(label) =>
              typeof label === "string" ? label : String(label)
            }
            formatter={(value) =>
              typeof value === "number"
                ? [FMT_USD.format(value), "Close"]
                : null
            }
          />
          <Area
            type="monotone"
            dataKey="close"
            stroke="#0ea5e9"
            strokeWidth={1.5}
            fill="url(#priceFill)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
