"use client";

/**
 * My Portfolio tab — import a CSV / paste tickers, analyse with the live
 * verification engine.
 *
 * Workflow:
 *   1. Pick an input method: paste shorthand ("AAPL 10, MSFT 5, JPM 20"),
 *      upload a Trading 212 CSV, or upload a generic CSV.
 *   2. Click Import. The backend normalises into `Holding[]`.
 *   3. Click Analyse. The backend prices each holding via yfinance, groups
 *      by sector, runs the correlation scan, surfaces concentration alerts,
 *      and returns a `PortfolioAnalysis`.
 *   4. Render holdings table, sector breakdown, concentration alerts,
 *      correlation heatmap, total value, portfolio volatility.
 *
 * No persistence — refresh = re-import. Consistent with the "anonymous,
 * in-memory only" scope decision.
 */

import { useMemo, useState } from "react";
import {
  analysePortfolio,
  importPortfolioCsv,
  importPortfolioHoldings,
  type ConcentrationAlert,
  type CorrelationMatrix,
  type Holding,
  type PortfolioAnalysis,
  type PricedHolding,
  type SectorExposure,
} from "@/lib/portfolio_import";

type InputMode = "paste" | "trading_212" | "generic_csv";

interface Props {
  onOpenCalculators?: () => void;
}

export function MyPortfolio({ onOpenCalculators }: Props) {
  const [inputMode, setInputMode] = useState<InputMode>("paste");
  const [pasteText, setPasteText] = useState("AAPL 10, MSFT 5, JPM 20, XOM 8");
  const [csvText, setCsvText] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [holdings, setHoldings] = useState<Holding[] | null>(null);
  const [importSource, setImportSource] = useState<string | null>(null);

  const [analysing, setAnalysing] = useState(false);
  const [analyseError, setAnalyseError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<PortfolioAnalysis | null>(null);

  async function handleImport() {
    setImportError(null);
    setHoldings(null);
    setAnalysis(null);
    setAnalyseError(null);
    setImporting(true);
    try {
      let imported;
      if (inputMode === "paste") {
        const parsed = parseShorthand(pasteText);
        if (parsed.length === 0) {
          throw new Error(
            "Couldn't parse any holdings. Try the format 'AAPL 10, MSFT 5'.",
          );
        }
        imported = await importPortfolioHoldings(parsed);
      } else {
        if (!csvText.trim()) {
          throw new Error("Paste the CSV contents first.");
        }
        imported = await importPortfolioCsv(csvText, inputMode);
      }
      setHoldings(imported.holdings);
      setImportSource(imported.source);
    } catch (e) {
      setImportError(e instanceof Error ? e.message : String(e));
    } finally {
      setImporting(false);
    }
  }

  async function handleAnalyse() {
    if (!holdings) return;
    setAnalysing(true);
    setAnalyseError(null);
    setAnalysis(null);
    try {
      const a = await analysePortfolio(holdings, 252);
      setAnalysis(a);
    } catch (e) {
      setAnalyseError(e instanceof Error ? e.message : String(e));
    } finally {
      setAnalysing(false);
    }
  }

  function handleFile(file: File) {
    void file.text().then(setCsvText);
  }

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-4 shadow-sm sm:p-6">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-indigo-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
            My portfolio
          </span>
          <h2 className="text-sm font-semibold text-zinc-900">
            Import + analyse
          </h2>
        </div>
        <p className="mt-2 max-w-3xl text-xs leading-relaxed text-zinc-700 sm:text-sm">
          Anonymous, in-memory only — your holdings live in this browser session
          and disappear on refresh. We never persist anything.
        </p>
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h3 className="text-sm font-semibold text-zinc-900">1. Import</h3>
        <div className="mt-3 inline-flex rounded-lg border border-zinc-300 bg-white p-0.5 shadow-sm">
          <ModeButton
            active={inputMode === "paste"}
            onClick={() => setInputMode("paste")}
          >
            Paste shorthand
          </ModeButton>
          <ModeButton
            active={inputMode === "trading_212"}
            onClick={() => setInputMode("trading_212")}
          >
            Trading 212 CSV
          </ModeButton>
          <ModeButton
            active={inputMode === "generic_csv"}
            onClick={() => setInputMode("generic_csv")}
          >
            Generic CSV
          </ModeButton>
        </div>

        {inputMode === "paste" ? (
          <div className="mt-4 space-y-2">
            <label className="block text-xs text-zinc-600">
              Format: <span className="font-mono">TICKER SHARES</span>{" "}
              comma-separated (e.g.{" "}
              <span className="font-mono">AAPL 10, MSFT 5</span>)
            </label>
            <textarea
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              className="h-24 w-full rounded-md border border-zinc-300 px-3 py-2 font-mono text-sm"
              placeholder="AAPL 10, MSFT 5, JPM 20"
            />
          </div>
        ) : (
          <div className="mt-4 space-y-2">
            <label className="block text-xs text-zinc-600">
              {inputMode === "trading_212"
                ? "Paste the CSV body from Trading 212's holdings export (or drop the file)."
                : "Any CSV with columns for ticker + shares (+ optional cost basis)."}
            </label>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
              className="text-xs"
            />
            <textarea
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              className="h-32 w-full rounded-md border border-zinc-300 px-3 py-2 font-mono text-[11px]"
              placeholder="Ticker,Quantity,Average price&#10;AAPL,10,175.32&#10;MSFT,5,420.00"
            />
          </div>
        )}

        <button
          type="button"
          onClick={handleImport}
          disabled={importing}
          className="mt-4 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:opacity-50"
        >
          {importing ? "Importing…" : "Import holdings"}
        </button>
        {importError && (
          <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
            {importError}
          </div>
        )}
        {holdings && (
          <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
            Imported {holdings.length} holdings from{" "}
            <span className="font-mono">{importSource}</span>.
          </div>
        )}
      </section>

      {holdings && (
        <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
          <h3 className="text-sm font-semibold text-zinc-900">2. Analyse</h3>
          <p className="mt-1 text-xs text-zinc-600">
            Prices each holding via yfinance, groups by sector, computes the
            correlation matrix, surfaces concentration alerts.
          </p>
          <button
            type="button"
            onClick={handleAnalyse}
            disabled={analysing}
            className="mt-3 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:opacity-50"
          >
            {analysing ? "Analysing…" : "Run analysis"}
          </button>
          {analyseError && (
            <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              {analyseError}
            </div>
          )}
        </section>
      )}

      {analysis && <AnalysisView analysis={analysis} />}

      {onOpenCalculators && (
        <p className="text-[11px] text-zinc-500">
          Want to optimise the basket instead?{" "}
          <button
            type="button"
            onClick={onOpenCalculators}
            className="font-medium text-indigo-700 hover:underline"
          >
            Open the Portfolio calculator →
          </button>
        </p>
      )}
    </div>
  );
}

// --- Analysis view ----------------------------------------------------------

function AnalysisView({ analysis }: { analysis: PortfolioAnalysis }) {
  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h3 className="text-sm font-semibold text-zinc-900">Headline</h3>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat
            label="Total value"
            value={formatUsd(analysis.total_value_usd)}
          />
          <Stat label="Holdings" value={String(analysis.holdings.length)} />
          <Stat
            label="Portfolio vol (annual)"
            value={
              analysis.portfolio_volatility_annualised !== null
                ? `${(analysis.portfolio_volatility_annualised * 100).toFixed(1)}%`
                : "—"
            }
          />
          <Stat label="Lookback" value={`${analysis.lookback_days}d`} />
        </div>
      </section>

      {analysis.concentration_alerts.length > 0 && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4 shadow-sm sm:p-6">
          <h3 className="text-sm font-semibold text-amber-900">
            Concentration alerts ({analysis.concentration_alerts.length})
          </h3>
          <ul className="mt-3 space-y-2">
            {analysis.concentration_alerts.map((a) => (
              <AlertRow key={`${a.kind}:${a.label}`} alert={a} />
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h3 className="text-sm font-semibold text-zinc-900">Holdings</h3>
        <HoldingsTable holdings={analysis.holdings} />
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h3 className="text-sm font-semibold text-zinc-900">Sector exposure</h3>
        <SectorBars sectors={analysis.sector_exposure} />
      </section>

      {analysis.correlation_matrix && (
        <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
          <h3 className="text-sm font-semibold text-zinc-900">
            Correlation matrix (252-day Pearson)
          </h3>
          <CorrelationHeatmap matrix={analysis.correlation_matrix} />
        </section>
      )}

      {analysis.limitations.length > 0 && (
        <section className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-xs text-zinc-700">
          <div className="font-semibold text-zinc-900">Notes</div>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {analysis.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function HoldingsTable({ holdings }: { holdings: PricedHolding[] }) {
  const sorted = useMemo(
    () => [...holdings].sort((a, b) => b.value_usd - a.value_usd),
    [holdings],
  );
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full min-w-[600px] text-xs">
        <thead className="bg-zinc-50 text-[10px] uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="px-2 py-1 text-left">Ticker</th>
            <th className="px-2 py-1 text-right">Shares</th>
            <th className="px-2 py-1 text-right">Spot</th>
            <th className="px-2 py-1 text-right">Value</th>
            <th className="px-2 py-1 text-right">Weight</th>
            <th className="px-2 py-1 text-right">P/L</th>
            <th className="px-2 py-1 text-left">Sector</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((h) => (
            <tr key={h.ticker} className="border-t border-zinc-100">
              <td className="px-2 py-1 font-mono font-semibold">{h.ticker}</td>
              <td className="px-2 py-1 text-right font-mono">{h.shares}</td>
              <td className="px-2 py-1 text-right font-mono">
                {h.spot.toFixed(2)}
              </td>
              <td className="px-2 py-1 text-right font-mono">
                {formatUsd(h.value_usd)}
              </td>
              <td className="px-2 py-1 text-right font-mono">
                {(h.weight * 100).toFixed(1)}%
              </td>
              <td
                className={`px-2 py-1 text-right font-mono ${
                  h.pnl_usd === null
                    ? "text-zinc-400"
                    : h.pnl_usd >= 0
                      ? "text-emerald-700"
                      : "text-rose-700"
                }`}
              >
                {h.pnl_usd === null
                  ? "—"
                  : `${h.pnl_usd >= 0 ? "+" : ""}${formatUsd(h.pnl_usd)}`}
              </td>
              <td className="px-2 py-1 text-zinc-700">{h.sector ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SectorBars({ sectors }: { sectors: SectorExposure[] }) {
  return (
    <div className="mt-3 space-y-2">
      {sectors.map((s) => (
        <div key={s.sector} className="text-xs">
          <div className="flex items-baseline justify-between">
            <span className="text-zinc-700">{s.sector}</span>
            <span className="font-mono text-zinc-900">
              {(s.weight * 100).toFixed(1)}% · {formatUsd(s.value_usd)}
            </span>
          </div>
          <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-zinc-100">
            <div
              className="h-full bg-indigo-500"
              style={{ width: `${Math.min(100, s.weight * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function CorrelationHeatmap({ matrix }: { matrix: CorrelationMatrix }) {
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="border-collapse text-[11px]">
        <thead>
          <tr>
            <th className="px-1 py-0.5"></th>
            {matrix.tickers.map((t) => (
              <th
                key={t}
                className="px-1 py-0.5 text-center font-mono font-semibold text-zinc-700"
              >
                {t}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.tickers.map((row, i) => (
            <tr key={row}>
              <td className="px-1 py-0.5 text-right font-mono font-semibold text-zinc-700">
                {row}
              </td>
              {matrix.matrix[i].map((v, j) => (
                <td
                  key={`${row}-${matrix.tickers[j]}`}
                  className="border border-white px-1 py-0.5 text-center font-mono"
                  style={{
                    backgroundColor: corrColor(v),
                    color: Math.abs(v) > 0.55 ? "white" : "#18181b",
                  }}
                  title={`corr(${row}, ${matrix.tickers[j]}) = ${v.toFixed(3)}`}
                >
                  {v.toFixed(2)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-[10px] text-zinc-500">
        Pearson correlation of daily returns over the last 252 trading days.
        Deep blue = strongly positive; deep red = strongly negative.
      </p>
    </div>
  );
}

function AlertRow({ alert }: { alert: ConcentrationAlert }) {
  return (
    <li className="flex items-start gap-2 text-xs text-amber-900">
      <span className="mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
      <div>
        <div className="font-semibold">
          {alert.kind === "single_position"
            ? "Single position"
            : "Sector concentration"}
          : {alert.label} ({(alert.weight * 100).toFixed(1)}%)
        </div>
        <div className="text-amber-800">{alert.message}</div>
      </div>
    </li>
  );
}

// --- Helpers ----------------------------------------------------------------

function parseShorthand(text: string): Holding[] {
  // Parse "AAPL 10, MSFT 5.5, JPM 20" or one-per-line.
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

function corrColor(v: number): string {
  // Map [-1, 1] → red ↔ white ↔ blue. Clamp to keep extreme noise in range.
  const x = Math.max(-1, Math.min(1, v));
  if (x >= 0) {
    // White (255,255,255) → blue (37,99,235)
    const t = x;
    const r = Math.round(255 - (255 - 37) * t);
    const g = Math.round(255 - (255 - 99) * t);
    const b = Math.round(255 - (255 - 235) * t);
    return `rgb(${r}, ${g}, ${b})`;
  }
  // White → red (220,38,38)
  const t = -x;
  const r = Math.round(255 - (255 - 220) * t);
  const g = Math.round(255 - (255 - 38) * t);
  const b = Math.round(255 - (255 - 38) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

function formatUsd(v: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
}

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
        active ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-100"
      }`}
    >
      {children}
    </button>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-white px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-zinc-500">
        {label}
      </div>
      <div className="font-mono text-sm font-semibold text-zinc-900">
        {value}
      </div>
    </div>
  );
}
