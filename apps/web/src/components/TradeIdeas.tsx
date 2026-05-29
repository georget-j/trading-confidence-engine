"use client";

/**
 * Trade Ideas tab — live ticker → position → verified scenario explorer.
 *
 * Workflow:
 *   1. Type a ticker, hit Load. Pulls spot + realised vol + sector via
 *      `/api/ticker/{ticker}/summary` (yfinance-backed).
 *   2. Optionally inspect the live options chain for a specific expiry.
 *   3. Build a single-leg option position. Days-to-expiry + IV pre-fill
 *      from the loaded ticker; the user can override either.
 *   4. Click Price. The position runs through the full verified options
 *      pipeline (BSM + binomial + Monte Carlo + Crank-Nicolson + invariants
 *      + per-method scorecard + trace drawer).
 *   5. Scenario Explorer below the result lets the user drag spot / vol /
 *      time and see verified P&L curves in real time.
 *
 * No recommendation logic here — Trade Ideas is just "use the engine on a
 * real ticker." Hedge Finder + Compare are where active recommendations
 * (and the heavier per-output disclaimers) live.
 */

import { useState } from "react";
import { priceOption } from "@/lib/api";
import {
  fetchExpiries,
  fetchOptionsChain,
  fetchTickerSummary,
  type OptionChainEntry,
  type OptionsChain,
  type TickerSummary,
} from "@/lib/ticker";
import type {
  FinalAnswer,
  OptionsPricingRequest,
  OptionType,
} from "@/lib/types";
import { ResultCard } from "./ResultCard";
import { ScenarioExplorer } from "./ScenarioExplorer";

interface Props {
  /** Backwards-compatible escape hatch — drop to the Calculators tab. */
  onOpenCalculators?: () => void;
}

export function TradeIdeas({ onOpenCalculators }: Props) {
  const [tickerInput, setTickerInput] = useState("TSLA");
  const [summary, setSummary] = useState<TickerSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const [expiries, setExpiries] = useState<string[]>([]);
  const [selectedExpiry, setSelectedExpiry] = useState<string | null>(null);
  const [chain, setChain] = useState<OptionsChain | null>(null);
  const [chainLoading, setChainLoading] = useState(false);
  const [chainError, setChainError] = useState<string | null>(null);

  // Position builder state — initialised from the loaded summary.
  const [optionType, setOptionType] = useState<OptionType>("call");
  const [strike, setStrike] = useState("");
  const [days, setDays] = useState("30");
  const [vol, setVol] = useState(""); // percent (e.g. 18 for 18%)
  const [rate, setRate] = useState("5");

  const [pricedAnswer, setPricedAnswer] = useState<FinalAnswer | null>(null);
  const [pricedRequest, setPricedRequest] =
    useState<OptionsPricingRequest | null>(null);
  const [pricing, setPricing] = useState(false);
  const [pricingError, setPricingError] = useState<string | null>(null);

  async function loadTicker() {
    if (!tickerInput.trim()) return;
    setSummaryError(null);
    setSummary(null);
    setExpiries([]);
    setSelectedExpiry(null);
    setChain(null);
    setSummaryLoading(true);
    try {
      const s = await fetchTickerSummary(tickerInput);
      setSummary(s);
      // Pre-fill the position builder from the loaded ticker.
      setStrike(Math.round(s.spot).toString());
      setVol(((s.realised_vol_annualised || 0.2) * 100).toFixed(1));
      // Fetch available expiries — non-blocking; ignore failure (some tickers
      // have no options chain).
      fetchExpiries(s.ticker)
        .then((r) => setExpiries(r.expiries))
        .catch(() => setExpiries([]));
    } catch (e) {
      setSummaryError(e instanceof Error ? e.message : String(e));
    } finally {
      setSummaryLoading(false);
    }
  }

  async function loadChain(expiry: string) {
    if (!summary) return;
    setSelectedExpiry(expiry);
    setChain(null);
    setChainError(null);
    setChainLoading(true);
    try {
      const c = await fetchOptionsChain(summary.ticker, expiry);
      setChain(c);
    } catch (e) {
      setChainError(e instanceof Error ? e.message : String(e));
    } finally {
      setChainLoading(false);
    }
  }

  function applyChainEntry(entry: OptionChainEntry) {
    setOptionType(entry.option_type);
    setStrike(entry.strike.toString());
    // If the chain entry has a non-null IV, prefer it over realised vol.
    if (entry.implied_volatility !== null && entry.implied_volatility > 0) {
      setVol((entry.implied_volatility * 100).toFixed(1));
    }
    if (selectedExpiry) {
      const expiryDate = new Date(selectedExpiry);
      const today = new Date();
      const diff = Math.max(
        1,
        Math.round(
          (expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
        ),
      );
      setDays(diff.toString());
    }
  }

  async function priceCurrentPosition() {
    if (!summary) return;
    const sNum = summary.spot;
    const kNum = Number(strike);
    const dNum = Number(days);
    const vNum = Number(vol);
    const rNum = Number(rate);
    if (
      !Number.isFinite(sNum) ||
      !Number.isFinite(kNum) ||
      !Number.isFinite(dNum) ||
      !Number.isFinite(vNum) ||
      !Number.isFinite(rNum) ||
      kNum <= 0 ||
      dNum <= 0 ||
      vNum <= 0
    ) {
      setPricingError("Fill in every field with a positive number first.");
      return;
    }
    const req: OptionsPricingRequest = {
      spot: sNum,
      strike: kNum,
      time_to_expiry_years: dNum / 365,
      volatility: vNum / 100,
      risk_free_rate: rNum / 100,
      dividend_yield: 0,
      option_type: optionType,
      style: "european",
    };
    setPricing(true);
    setPricingError(null);
    setPricedAnswer(null);
    try {
      const a = await priceOption(req);
      setPricedAnswer(a);
      setPricedRequest(req);
    } catch (e) {
      setPricingError(e instanceof Error ? e.message : String(e));
    } finally {
      setPricing(false);
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-4 shadow-sm sm:p-6">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-indigo-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
            Trade ideas
          </span>
          <h2 className="text-sm font-semibold text-zinc-900">
            Live ticker → verified scenario
          </h2>
        </div>
        <p className="mt-2 max-w-3xl text-xs leading-relaxed text-zinc-700 sm:text-sm">
          Pick any US-listed ticker. Build an option position from the loaded
          spot + realised vol (or pick a strike from the live chain), then watch
          the verified P&amp;L curve under spot / vol / time shocks.
        </p>
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h3 className="text-sm font-semibold text-zinc-900">Ticker</h3>
        <p className="mt-1 text-xs text-zinc-600">
          Try TSLA, AAPL, SPY, NVDA, MSFT.
        </p>
        <form
          className="mt-3 flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            loadTicker();
          }}
        >
          <input
            type="text"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm font-mono uppercase sm:max-w-xs"
            placeholder="e.g. TSLA"
            spellCheck={false}
          />
          <button
            type="submit"
            disabled={summaryLoading}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:opacity-50"
          >
            {summaryLoading ? "Loading…" : "Load ticker"}
          </button>
        </form>
        {summaryError && (
          <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
            {summaryError}
          </div>
        )}
        {summary && <TickerSummaryCard summary={summary} />}
      </section>

      {summary && expiries.length > 0 && (
        <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
          <h3 className="text-sm font-semibold text-zinc-900">
            Live options chain
          </h3>
          <p className="mt-1 text-xs text-zinc-600">
            Pick an expiry to load strikes. Click any row to copy it into the
            position builder.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {expiries.slice(0, 8).map((e) => {
              const active = e === selectedExpiry;
              return (
                <button
                  key={e}
                  type="button"
                  onClick={() => loadChain(e)}
                  className={`rounded-md border px-3 py-1.5 text-xs font-mono transition ${
                    active
                      ? "border-zinc-900 bg-zinc-900 text-white"
                      : "border-zinc-300 hover:bg-zinc-50"
                  }`}
                >
                  {e}
                </button>
              );
            })}
          </div>
          {chainLoading && (
            <div className="mt-3 text-xs text-zinc-500">Loading chain…</div>
          )}
          {chainError && (
            <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              {chainError}
            </div>
          )}
          {chain && <ChainTable chain={chain} onPick={applyChainEntry} />}
        </section>
      )}

      {summary && (
        <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
          <h3 className="text-sm font-semibold text-zinc-900">
            Position builder
          </h3>
          <p className="mt-1 text-xs text-zinc-600">
            Spot pulls from the live quote ({summary.spot.toFixed(2)}{" "}
            {summary.spot_currency}). Override strike / days / IV / rate to test
            a hypothesis.
          </p>
          <form
            className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3"
            onSubmit={(e) => {
              e.preventDefault();
              priceCurrentPosition();
            }}
          >
            <label className="block text-xs">
              <span className="text-zinc-600">Option type</span>
              <select
                value={optionType}
                onChange={(e) => setOptionType(e.target.value as OptionType)}
                className="mt-1 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm"
              >
                <option value="call">Call</option>
                <option value="put">Put</option>
              </select>
            </label>
            <NumField label="Strike" value={strike} onChange={setStrike} />
            <NumField label="Days to expiry" value={days} onChange={setDays} />
            <NumField label="IV (%)" value={vol} onChange={setVol} />
            <NumField
              label="Risk-free rate (%)"
              value={rate}
              onChange={setRate}
            />
            <button
              type="submit"
              disabled={pricing}
              className="self-end rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:opacity-50"
            >
              {pricing ? "Pricing…" : "Price this position"}
            </button>
          </form>
          {pricingError && (
            <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              {pricingError}
            </div>
          )}
        </section>
      )}

      {pricedAnswer && pricedRequest && (
        <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
          <ResultCard answer={pricedAnswer} request={pricedRequest} />
        </section>
      )}

      {pricedAnswer &&
        pricedRequest &&
        pricedAnswer.primary_result.kind === "options_price" && (
          <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
            <ScenarioExplorer
              baseRequest={pricedRequest}
              baseResult={pricedAnswer.primary_result}
            />
          </section>
        )}

      {onOpenCalculators && (
        <p className="text-[11px] text-zinc-500">
          Want to compare BSM vs binomial vs Monte Carlo vs Crank-Nicolson on
          the same inputs?{" "}
          <button
            type="button"
            onClick={onOpenCalculators}
            className="font-medium text-indigo-700 hover:underline"
          >
            Open the Methods Lab →
          </button>
        </p>
      )}
    </div>
  );
}

// --- Sub-components ---------------------------------------------------------

function TickerSummaryCard({ summary }: { summary: TickerSummary }) {
  return (
    <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs">
      <div className="flex items-baseline justify-between gap-2">
        <div>
          <div className="font-mono text-zinc-500">{summary.ticker}</div>
          <div className="mt-0.5 text-sm font-semibold text-zinc-900">
            {summary.long_name ?? summary.short_name ?? summary.ticker}
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-xl font-semibold text-zinc-900">
            {summary.spot.toFixed(2)}{" "}
            <span className="text-xs text-zinc-500">
              {summary.spot_currency}
            </span>
          </div>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat
          label="Realised vol (30d)"
          value={`${(summary.realised_vol_annualised * 100).toFixed(1)}%`}
        />
        <Stat label="Sector" value={summary.sector ?? "—"} />
        <Stat label="Industry" value={summary.industry ?? "—"} />
        <Stat
          label="Market cap"
          value={
            summary.market_cap !== null ? formatCap(summary.market_cap) : "—"
          }
        />
      </div>
    </div>
  );
}

function ChainTable({
  chain,
  onPick,
}: {
  chain: OptionsChain;
  onPick: (e: OptionChainEntry) => void;
}) {
  // Focus the table on strikes within ±20% of spot — the chain can be huge.
  const min = chain.spot * 0.8;
  const max = chain.spot * 1.2;
  const visible = chain.entries.filter(
    (e) => e.strike >= min && e.strike <= max,
  );
  // Group by strike so we can show call + put side-by-side.
  const byStrike = new Map<
    number,
    { call?: OptionChainEntry; put?: OptionChainEntry }
  >();
  for (const e of visible) {
    const row = byStrike.get(e.strike) ?? {};
    if (e.option_type === "call") row.call = e;
    else row.put = e;
    byStrike.set(e.strike, row);
  }
  const strikes = [...byStrike.keys()].sort((a, b) => a - b);

  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full min-w-[480px] text-xs">
        <thead className="bg-zinc-50 text-[10px] uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="px-2 py-1 text-left">Call</th>
            <th className="px-2 py-1 text-right">Call IV</th>
            <th className="px-2 py-1 text-center font-mono text-zinc-900">
              Strike
            </th>
            <th className="px-2 py-1 text-left">Put IV</th>
            <th className="px-2 py-1 text-right">Put</th>
          </tr>
        </thead>
        <tbody>
          {strikes.map((k) => {
            const { call, put } = byStrike.get(k)!;
            const atm = Math.abs(k - chain.spot) <= chain.spot * 0.01;
            return (
              <tr
                key={k}
                className={atm ? "bg-amber-50" : "border-t border-zinc-100"}
              >
                <td className="px-2 py-1 font-mono">
                  {call ? (
                    <button
                      type="button"
                      onClick={() => onPick(call)}
                      className="text-indigo-700 hover:underline"
                    >
                      {call.last_price !== null
                        ? call.last_price.toFixed(2)
                        : "—"}
                    </button>
                  ) : (
                    <span className="text-zinc-400">—</span>
                  )}
                </td>
                <td className="px-2 py-1 text-right font-mono text-zinc-500">
                  {call?.implied_volatility !== null &&
                  call?.implied_volatility !== undefined
                    ? `${(call.implied_volatility * 100).toFixed(1)}%`
                    : "—"}
                </td>
                <td className="px-2 py-1 text-center font-mono font-semibold">
                  {k.toFixed(0)}
                </td>
                <td className="px-2 py-1 font-mono text-zinc-500">
                  {put?.implied_volatility !== null &&
                  put?.implied_volatility !== undefined
                    ? `${(put.implied_volatility * 100).toFixed(1)}%`
                    : "—"}
                </td>
                <td className="px-2 py-1 text-right font-mono">
                  {put ? (
                    <button
                      type="button"
                      onClick={() => onPick(put)}
                      className="text-indigo-700 hover:underline"
                    >
                      {put.last_price !== null
                        ? put.last_price.toFixed(2)
                        : "—"}
                    </button>
                  ) : (
                    <span className="text-zinc-400">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 text-[10px] text-zinc-500">
        Showing strikes within ±20% of spot ({chain.entries.length} contracts
        total). Click a price to copy it into the position builder.
      </p>
    </div>
  );
}

function NumField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (s: string) => void;
}) {
  return (
    <label className="block text-xs">
      <span className="text-zinc-600">{label}</span>
      <input
        type="number"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm font-mono"
        required
      />
    </label>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-white px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-zinc-500">
        {label}
      </div>
      <div className="text-xs font-semibold text-zinc-900">{value}</div>
    </div>
  );
}

function formatCap(v: number): string {
  if (v >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  return v.toFixed(0);
}
