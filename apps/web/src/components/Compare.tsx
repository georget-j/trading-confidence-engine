"use client";

/**
 * Compare tab — similar-sentiment peer comparison.
 *
 * Pick a ticker; we return ranked peers from the bundled universe by
 * Pearson return correlation over the lookback. Optional cheaper-only
 * filter narrows to peers materially smaller in market cap.
 */

import { useState } from "react";
import {
  fetchPeers,
  type PeerCandidate,
  type PeerComparisonResponse,
} from "@/lib/compare";

interface Props {
  onOpenCalculators?: () => void;
}

export function Compare({ onOpenCalculators }: Props) {
  const [tickerInput, setTickerInput] = useState("NVDA");
  const [lookback, setLookback] = useState("126");
  const [topK, setTopK] = useState("10");
  const [minCorr, setMinCorr] = useState("50"); // percent
  const [cheaperOnly, setCheaperOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resp, setResp] = useState<PeerComparisonResponse | null>(null);

  async function handleRun() {
    if (!tickerInput.trim()) return;
    setError(null);
    setResp(null);
    setLoading(true);
    try {
      const r = await fetchPeers({
        ticker: tickerInput,
        lookbackDays: Number(lookback),
        topK: Number(topK),
        minCorrelation: Number(minCorr) / 100,
        cheaperOnly,
      });
      setResp(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-4 shadow-sm sm:p-6">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-indigo-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
            Compare
          </span>
          <h2 className="text-sm font-semibold text-zinc-900">
            Similar-sentiment peers
          </h2>
        </div>
        <p className="mt-2 max-w-3xl text-xs leading-relaxed text-zinc-700 sm:text-sm">
          Pick a ticker — we&apos;ll rank the bundled universe by daily-return
          correlation over your lookback. Optional &quot;cheaper than&quot;
          filter narrows to peers with materially smaller market cap.
        </p>
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h3 className="text-sm font-semibold text-zinc-900">Inputs</h3>
        <form
          className="mt-3 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            handleRun();
          }}
        >
          <label className="block text-xs">
            <span className="text-zinc-600">Reference ticker</span>
            <input
              type="text"
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
              className="mt-1 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm font-mono sm:max-w-xs"
              placeholder="NVDA"
              spellCheck={false}
              required
            />
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <NumField
              label="Lookback (days)"
              value={lookback}
              onChange={setLookback}
            />
            <NumField label="Top K" value={topK} onChange={setTopK} />
            <NumField
              label="Min correlation (%)"
              value={minCorr}
              onChange={setMinCorr}
            />
          </div>
          <label className="flex items-center gap-2 text-xs text-zinc-700">
            <input
              type="checkbox"
              checked={cheaperOnly}
              onChange={(e) => setCheaperOnly(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-400"
            />
            Cheaper-than-reference only (market cap &lt; 50% of reference)
          </label>
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:opacity-50"
          >
            {loading ? "Searching…" : "Find peers"}
          </button>
        </form>
        {error && (
          <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
            {error}
          </div>
        )}
      </section>

      {resp && <PeerResults resp={resp} />}

      {onOpenCalculators && (
        <p className="text-[11px] text-zinc-500">
          Want to dig into one peer&apos;s methods directly?{" "}
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

function PeerResults({ resp }: { resp: PeerComparisonResponse }) {
  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h3 className="text-sm font-semibold text-zinc-900">
          Reference: {resp.reference_ticker}
          {resp.reference_name && resp.reference_name !== resp.reference_ticker
            ? ` — ${resp.reference_name}`
            : ""}
        </h3>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat
            label="Spot"
            value={
              resp.reference_spot !== null
                ? `$${resp.reference_spot.toFixed(2)}`
                : "—"
            }
          />
          <Stat label="Sector" value={resp.reference_sector ?? "—"} />
          <Stat label="Industry" value={resp.reference_industry ?? "—"} />
          <Stat
            label="Market cap"
            value={
              resp.reference_market_cap !== null
                ? formatCap(resp.reference_market_cap)
                : "—"
            }
          />
        </div>
        <p className="mt-3 text-[11px] text-zinc-500">
          {resp.peers.length} peer{resp.peers.length === 1 ? "" : "s"} returned
          from a universe of {resp.universe_size} tickers · {resp.lookback_days}
          -day lookback.
        </p>
      </section>

      {resp.peers.length === 0 ? (
        <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6 text-xs text-zinc-600">
          No peers cleared the correlation threshold. Lower it (or turn off the
          cheaper-only filter) and try again.
        </section>
      ) : (
        <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
          <h3 className="text-sm font-semibold text-zinc-900">Peers</h3>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[640px] text-xs">
              <thead className="bg-zinc-50 text-[10px] uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-2 py-1 text-left">Ticker</th>
                  <th className="px-2 py-1 text-left">Name</th>
                  <th className="px-2 py-1 text-left">Sector</th>
                  <th className="px-2 py-1 text-right">Spot</th>
                  <th className="px-2 py-1 text-right">Market cap</th>
                  <th className="px-2 py-1 text-right">Correlation</th>
                  <th className="px-2 py-1 text-left">Tags</th>
                </tr>
              </thead>
              <tbody>
                {resp.peers.map((p) => (
                  <PeerRow key={p.ticker} p={p} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {resp.limitations.length > 0 && (
        <section className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-xs text-zinc-700">
          <div className="font-semibold text-zinc-900">Notes</div>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {resp.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-[11px] text-amber-900">
        Historical similarity is not future similarity. Companies in the same
        sector can decouple sharply during earnings, sector rotation, or
        idiosyncratic events. Not investment advice.
      </section>
    </div>
  );
}

function PeerRow({ p }: { p: PeerCandidate }) {
  const corrColor =
    p.correlation > 0.7
      ? "text-emerald-700"
      : p.correlation > 0.3
        ? "text-zinc-700"
        : "text-rose-700";
  return (
    <tr className="border-t border-zinc-100">
      <td className="px-2 py-1 font-mono font-semibold">{p.ticker}</td>
      <td className="px-2 py-1 text-zinc-700">{p.name}</td>
      <td className="px-2 py-1 text-zinc-600">{p.sector}</td>
      <td className="px-2 py-1 text-right font-mono">
        {p.spot !== null ? `$${p.spot.toFixed(2)}` : "—"}
      </td>
      <td className="px-2 py-1 text-right font-mono">
        {p.market_cap !== null ? formatCap(p.market_cap) : "—"}
      </td>
      <td className={`px-2 py-1 text-right font-mono ${corrColor}`}>
        {p.correlation.toFixed(3)}
      </td>
      <td className="px-2 py-1">
        <div className="flex flex-wrap gap-1">
          {p.same_industry && (
            <span className="inline-block rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-900">
              same industry
            </span>
          )}
          {p.is_cheaper && (
            <span className="inline-block rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-900">
              cheaper
            </span>
          )}
        </div>
      </td>
    </tr>
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
      <div className="font-mono text-xs font-semibold text-zinc-900">
        {value}
      </div>
    </div>
  );
}

function formatCap(v: number): string {
  if (v >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  return v.toFixed(0);
}
