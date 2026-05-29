"use client";

/**
 * Hedge Finder tab — anti-correlated hedge candidates per concentrated sector.
 *
 * Workflow:
 *   1. Paste your portfolio shorthand (same format as My Portfolio).
 *   2. Pick a lookback + min sector weight + top-K.
 *   3. Click Suggest. Backend prices the book, identifies concentrated
 *      sectors, scans the bundled universe for negatively-correlated
 *      candidates, and returns ranked baskets.
 *   4. Render one card per sector with the top-K candidates, their
 *      correlation, recent-window correlation, and a regime-shift warning
 *      when the two diverge.
 *
 * Every recommendation card carries the inline "not investment advice"
 * framing — these are based on historical correlations only.
 */

import { useState } from "react";
import {
  suggestHedges,
  type HedgeCandidate,
  type HedgeSuggestResponse,
  type SectorHedgeSuggestion,
} from "@/lib/hedge";
import type { Holding } from "@/lib/portfolio_import";

interface Props {
  onOpenCalculators?: () => void;
}

export function HedgeFinder({ onOpenCalculators }: Props) {
  const [pasteText, setPasteText] = useState("AAPL 20, MSFT 10, NVDA 5, JPM 2");
  const [lookback, setLookback] = useState("504");
  const [topK, setTopK] = useState("5");
  const [minWeight, setMinWeight] = useState("25"); // percent
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resp, setResp] = useState<HedgeSuggestResponse | null>(null);

  async function handleRun() {
    setError(null);
    setResp(null);
    const holdings = parseShorthand(pasteText);
    if (holdings.length === 0) {
      setError(
        "Couldn't parse any holdings. Use the format 'AAPL 10, MSFT 5'.",
      );
      return;
    }
    setLoading(true);
    try {
      const r = await suggestHedges({
        holdings,
        lookback_days: Number(lookback),
        top_k: Number(topK),
        min_sector_weight: Number(minWeight) / 100,
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
            Hedge finder
          </span>
          <h2 className="text-sm font-semibold text-zinc-900">
            Anti-correlated baskets
          </h2>
        </div>
        <p className="mt-2 max-w-3xl text-xs leading-relaxed text-zinc-700 sm:text-sm">
          For every sector that&apos;s over your concentration threshold, this
          scans a bundled universe of ~50 sector ETFs + large-cap stocks +
          asset-class hedges (TLT, GLD, SQQQ…) and returns the most
          negatively-correlated candidates over your lookback window.
        </p>
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h3 className="text-sm font-semibold text-zinc-900">Inputs</h3>
        <div className="mt-3 space-y-3">
          <label className="block text-xs text-zinc-600">
            Holdings (TICKER SHARES, comma-separated)
            <textarea
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              className="mt-1 h-20 w-full rounded-md border border-zinc-300 px-3 py-2 font-mono text-sm"
            />
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <NumField
              label="Lookback (days)"
              value={lookback}
              onChange={setLookback}
            />
            <NumField
              label="Top K per sector"
              value={topK}
              onChange={setTopK}
            />
            <NumField
              label="Min sector weight (%)"
              value={minWeight}
              onChange={setMinWeight}
            />
          </div>
          <button
            type="button"
            onClick={handleRun}
            disabled={loading}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:opacity-50"
          >
            {loading ? "Scanning universe…" : "Suggest hedges"}
          </button>
          {error && (
            <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              {error}
            </div>
          )}
        </div>
      </section>

      {resp && <SuggestionsView resp={resp} />}

      {onOpenCalculators && (
        <p className="text-[11px] text-zinc-500">
          Want to backtest a combined book?{" "}
          <button
            type="button"
            onClick={onOpenCalculators}
            className="font-medium text-indigo-700 hover:underline"
          >
            Open the Backtest calculator →
          </button>
        </p>
      )}
    </div>
  );
}

// --- Suggestions view -------------------------------------------------------

function SuggestionsView({ resp }: { resp: HedgeSuggestResponse }) {
  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4 shadow-sm sm:p-6">
        <div className="text-xs font-semibold uppercase tracking-wide text-amber-900">
          Disclaimer
        </div>
        <p className="mt-2 text-xs leading-relaxed text-amber-900">
          {resp.disclaimer}
        </p>
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h3 className="text-sm font-semibold text-zinc-900">Summary</h3>
        <p className="mt-2 text-xs text-zinc-600">
          Scanned {resp.universe_size} universe tickers over{" "}
          {resp.lookback_days} trading days. Returned {resp.suggestions.length}{" "}
          sector suggestion
          {resp.suggestions.length === 1 ? "" : "s"}.
        </p>
        {resp.limitations.length > 0 && (
          <ul className="mt-3 list-disc space-y-0.5 pl-4 text-xs text-zinc-600">
            {resp.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        )}
      </section>

      {resp.suggestions.length === 0 && (
        <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm sm:p-6 text-xs text-emerald-900">
          No sectors crossed the concentration threshold — your book is already
          diversified across sectors. Lower the threshold above if you still
          want to see candidates.
        </section>
      )}

      {resp.suggestions.map((s) => (
        <SectorSuggestionCard key={s.sector} suggestion={s} />
      ))}
    </div>
  );
}

function SectorSuggestionCard({
  suggestion,
}: {
  suggestion: SectorHedgeSuggestion;
}) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-zinc-900">
          Hedge candidates for {suggestion.sector}
        </h3>
        <span className="font-mono text-xs text-zinc-600">
          sector weight {(suggestion.sector_weight * 100).toFixed(1)}%
        </span>
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[640px] text-xs">
          <thead className="bg-zinc-50 text-[10px] uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-2 py-1 text-left">Ticker</th>
              <th className="px-2 py-1 text-left">Name</th>
              <th className="px-2 py-1 text-left">Universe sector</th>
              <th className="px-2 py-1 text-right">Full-window corr</th>
              <th className="px-2 py-1 text-right">Recent corr</th>
              <th className="px-2 py-1 text-left">Flag</th>
            </tr>
          </thead>
          <tbody>
            {suggestion.candidates.map((c) => (
              <CandidateRow key={c.ticker} c={c} />
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[11px] text-zinc-500">
        Correlations are Pearson over daily returns. Recent = trailing ~6
        months. A flagged row means the recent correlation has drifted by more
        than 0.30 from the full-window value — historically reliable hedges can
        weaken or flip in new market regimes.
      </p>
    </section>
  );
}

function CandidateRow({ c }: { c: HedgeCandidate }) {
  const corrColor =
    c.correlation < -0.5
      ? "text-emerald-700"
      : c.correlation < 0
        ? "text-zinc-700"
        : "text-rose-700";
  return (
    <tr className="border-t border-zinc-100">
      <td className="px-2 py-1 font-mono font-semibold">{c.ticker}</td>
      <td className="px-2 py-1 text-zinc-700">{c.name}</td>
      <td className="px-2 py-1 text-zinc-600">{c.universe_sector}</td>
      <td className={`px-2 py-1 text-right font-mono ${corrColor}`}>
        {c.correlation.toFixed(3)}
      </td>
      <td className="px-2 py-1 text-right font-mono text-zinc-600">
        {c.recent_correlation.toFixed(3)}
      </td>
      <td className="px-2 py-1">
        {c.half_life_warning ? (
          <span
            className="inline-block rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900"
            title="Recent correlation differs from the full window by >0.30"
          >
            regime shift
          </span>
        ) : (
          <span className="text-[10px] text-zinc-400">stable</span>
        )}
      </td>
    </tr>
  );
}

// --- Helpers ----------------------------------------------------------------

function parseShorthand(text: string): Holding[] {
  return text
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s): Holding | null => {
      const m = s.match(/^([A-Za-z.\-]+)\s+([0-9.,]+)$/);
      if (!m) return null;
      const ticker = m[1].toUpperCase();
      const shares = Number(m[2].replace(",", ""));
      if (!Number.isFinite(shares) || shares <= 0) return null;
      return { ticker, shares };
    })
    .filter((h): h is Holding => h !== null);
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
