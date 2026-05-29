"use client";

/**
 * Methods Lab — invoke a single calculator directly with raw inputs.
 *
 * Three-column layout on desktop, stacked on mobile:
 *   1. Method picker (grouped by family)
 *   2. Input form (family-specific — small handwritten forms keyed off the
 *      selected method's family rather than a generic schema-driven generator)
 *   3. Raw result panel — shows the unaltered `CalculatorResult`. No
 *      cross-method check, no invariants, no sensitivity. By design.
 *
 * Built for the "advanced user wants to see what one method says" workflow
 * Phase 5e backend already supports; the only thing missing was a surface.
 */

import { useEffect, useState } from "react";
import {
  listLabMethods,
  runLabMethod,
  type LabFamily,
  type LabRunResponse,
  type MethodDescriptor,
} from "@/lib/lab";
import type {
  BacktestPayload,
  OptionsPriceResult,
  PortfolioPayload,
  VaRPayload,
} from "@/lib/types";

const FAMILY_LABEL: Record<LabFamily, string> = {
  options: "Options pricing",
  var: "Value at Risk",
  portfolio: "Portfolio optimisation",
  backtest: "Backtesting",
};

const COST_COLOR: Record<MethodDescriptor["cost"], string> = {
  negligible: "bg-emerald-100 text-emerald-900",
  cheap: "bg-emerald-100 text-emerald-900",
  moderate: "bg-amber-100 text-amber-900",
  expensive: "bg-rose-100 text-rose-900",
};

export function MethodsLab() {
  const [methods, setMethods] = useState<MethodDescriptor[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [response, setResponse] = useState<LabRunResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    listLabMethods()
      .then((m) => {
        if (cancelled) return;
        setMethods(m);
        setSelectedId(m[0]?.method_id ?? null);
      })
      .catch((e: unknown) =>
        setLoadError(e instanceof Error ? e.message : String(e)),
      );
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = methods?.find((m) => m.method_id === selectedId) ?? null;

  async function handleRun(inputs: Record<string, unknown>) {
    if (!selected) return;
    setRunning(true);
    setRunError(null);
    setResponse(null);
    try {
      const r = await runLabMethod({
        method_id: selected.method_id,
        inputs,
      });
      setResponse(r);
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  if (loadError) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
        Could not load Methods Lab catalog: {loadError}
      </div>
    );
  }
  if (methods === null) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
        Loading Methods Lab catalog…
      </div>
    );
  }

  // Reset response/error whenever the selection changes so the right column
  // never shows stale data attributed to the wrong method.
  function selectMethod(id: string) {
    if (id === selectedId) return;
    setSelectedId(id);
    setResponse(null);
    setRunError(null);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1fr_1.2fr]">
      <MethodPicker
        methods={methods}
        selectedId={selectedId}
        onSelect={selectMethod}
      />
      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h2 className="mb-1 text-sm font-semibold text-zinc-900">Inputs</h2>
        {selected ? (
          <>
            <p className="mb-4 text-xs leading-relaxed text-zinc-600">
              Raw inputs for{" "}
              <span className="font-mono text-zinc-900">
                {selected.method_id}
              </span>
              . No cross-check, no invariants — just this one method.
            </p>
            <LabInputForm
              family={selected.family}
              running={running}
              onRun={handleRun}
            />
          </>
        ) : (
          <p className="text-xs text-zinc-500">
            Pick a method from the left to begin.
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <h2 className="mb-4 text-sm font-semibold text-zinc-900">Raw result</h2>
        {running && (
          <div className="text-sm text-zinc-500">
            Running {selected?.method_name}…
          </div>
        )}
        {runError && (
          <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
            <div className="mb-1 font-semibold">Run failed</div>
            <pre className="whitespace-pre-wrap font-mono text-[11px]">
              {runError}
            </pre>
          </div>
        )}
        {!running && !runError && !response && (
          <p className="text-xs text-zinc-500">
            Fill the form and press Run to see this method&apos;s raw output.
          </p>
        )}
        {response && <LabResult response={response} />}
      </section>
    </div>
  );
}

// --- Picker -----------------------------------------------------------------

function MethodPicker({
  methods,
  selectedId,
  onSelect,
}: {
  methods: MethodDescriptor[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const byFamily = methods.reduce<Record<LabFamily, MethodDescriptor[]>>(
    (acc, m) => {
      (acc[m.family] ||= []).push(m);
      return acc;
    },
    { options: [], var: [], portfolio: [], backtest: [] },
  );

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
      <h2 className="mb-2 text-sm font-semibold text-zinc-900">
        Methods ({methods.length})
      </h2>
      <p className="mb-4 text-xs leading-relaxed text-zinc-600">
        Every independent calculator method this engine knows about. Pick one to
        run it on its own.
      </p>
      <div className="space-y-5">
        {(Object.keys(byFamily) as LabFamily[]).map((fam) => {
          const ms = byFamily[fam];
          if (ms.length === 0) return null;
          return (
            <div key={fam}>
              <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                {FAMILY_LABEL[fam]}
              </div>
              <ul className="space-y-1.5">
                {ms.map((m) => {
                  const active = m.method_id === selectedId;
                  return (
                    <li key={m.method_id}>
                      <button
                        type="button"
                        onClick={() => onSelect(m.method_id)}
                        className={`w-full rounded-md border px-3 py-2 text-left text-xs transition ${
                          active
                            ? "border-zinc-900 bg-zinc-50 ring-1 ring-zinc-900"
                            : "border-zinc-200 hover:bg-zinc-50"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <div className="font-semibold text-zinc-900">
                              {m.method_name}
                            </div>
                            <div className="mt-0.5 text-[11px] leading-snug text-zinc-600">
                              {m.one_line}
                            </div>
                          </div>
                          <span
                            className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase ${COST_COLOR[m.cost]}`}
                          >
                            {m.cost}
                          </span>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// --- Per-family input forms -------------------------------------------------

function LabInputForm({
  family,
  running,
  onRun,
}: {
  family: LabFamily;
  running: boolean;
  onRun: (inputs: Record<string, unknown>) => void;
}) {
  if (family === "options")
    return <OptionsForm running={running} onRun={onRun} />;
  if (family === "var") return <VarForm running={running} onRun={onRun} />;
  if (family === "portfolio")
    return <PortfolioForm running={running} onRun={onRun} />;
  return <BacktestForm running={running} onRun={onRun} />;
}

function OptionsForm({
  running,
  onRun,
}: {
  running: boolean;
  onRun: (inputs: Record<string, unknown>) => void;
}) {
  const [spot, setSpot] = useState("450");
  const [strike, setStrike] = useState("450");
  const [tte, setTte] = useState("30");
  const [vol, setVol] = useState("18");
  const [r, setR] = useState("5");
  const [q, setQ] = useState("0");
  const [type, setType] = useState<"call" | "put">("call");

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        onRun({
          spot: Number(spot),
          strike: Number(strike),
          time_to_expiry_years: Number(tte) / 365,
          volatility: Number(vol) / 100,
          risk_free_rate: Number(r) / 100,
          dividend_yield: Number(q) / 100,
          option_type: type,
        });
      }}
    >
      <div className="grid grid-cols-2 gap-3">
        <NumField label="Spot ($)" value={spot} onChange={setSpot} />
        <NumField label="Strike ($)" value={strike} onChange={setStrike} />
        <NumField label="Days to expiry" value={tte} onChange={setTte} />
        <NumField label="Volatility (%)" value={vol} onChange={setVol} />
        <NumField label="Risk-free rate (%)" value={r} onChange={setR} />
        <NumField label="Dividend yield (%)" value={q} onChange={setQ} />
      </div>
      <label className="block text-xs">
        <span className="text-zinc-600">Option type</span>
        <select
          value={type}
          onChange={(e) => setType(e.target.value as "call" | "put")}
          className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm"
        >
          <option value="call">Call</option>
          <option value="put">Put</option>
        </select>
      </label>
      <RunButton running={running} />
    </form>
  );
}

function VarForm({
  running,
  onRun,
}: {
  running: boolean;
  onRun: (inputs: Record<string, unknown>) => void;
}) {
  const [ticker, setTicker] = useState("SPY");
  const [lookback, setLookback] = useState("504");
  const [confidence, setConfidence] = useState("99");
  const [horizon, setHorizon] = useState("1");
  const [portValue, setPortValue] = useState("50000");

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        onRun({
          ticker,
          lookback_days: Number(lookback),
          confidence_level: Number(confidence) / 100,
          horizon_days: Number(horizon),
          portfolio_value: Number(portValue),
        });
      }}
    >
      <div className="grid grid-cols-2 gap-3">
        <TextField label="Ticker" value={ticker} onChange={setTicker} />
        <NumField
          label="Lookback (days)"
          value={lookback}
          onChange={setLookback}
        />
        <NumField
          label="Confidence (%)"
          value={confidence}
          onChange={setConfidence}
        />
        <NumField
          label="Horizon (days)"
          value={horizon}
          onChange={setHorizon}
        />
        <NumField
          label="Portfolio value ($)"
          value={portValue}
          onChange={setPortValue}
        />
      </div>
      <RunButton running={running} />
    </form>
  );
}

function PortfolioForm({
  running,
  onRun,
}: {
  running: boolean;
  onRun: (inputs: Record<string, unknown>) => void;
}) {
  const [tickers, setTickers] = useState("SPY,QQQ,GLD,TLT");
  const [lookback, setLookback] = useState("252");
  const [gamma, setGamma] = useState("2.0");
  const [maxWeight, setMaxWeight] = useState("60");

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        onRun({
          tickers: tickers
            .split(",")
            .map((t) => t.trim().toUpperCase())
            .filter((t) => t.length > 0),
          lookback_days: Number(lookback),
          // The lab dispatcher reads `objective` from the request; we omit it
          // here because each method picks its own. The PortfolioRequest
          // schema requires it, so default to mean_variance — solver-specific
          // methods ignore it where it's not applicable.
          objective: "mean_variance",
          risk_aversion: Number(gamma),
          max_weight: Number(maxWeight) / 100,
        });
      }}
    >
      <TextField
        label="Tickers (comma-separated)"
        value={tickers}
        onChange={setTickers}
      />
      <div className="grid grid-cols-2 gap-3">
        <NumField
          label="Lookback (days)"
          value={lookback}
          onChange={setLookback}
        />
        <NumField label="Risk aversion γ" value={gamma} onChange={setGamma} />
        <NumField
          label="Max weight (%)"
          value={maxWeight}
          onChange={setMaxWeight}
        />
      </div>
      <RunButton running={running} />
    </form>
  );
}

function BacktestForm({
  running,
  onRun,
}: {
  running: boolean;
  onRun: (inputs: Record<string, unknown>) => void;
}) {
  const [ticker, setTicker] = useState("SPY");
  const [lookback, setLookback] = useState("252");
  const [capital, setCapital] = useState("100000");
  const [slippage, setSlippage] = useState("5");

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        // Note: the lab dispatcher infers `strategy` from method_id, so we
        // don't include it in inputs.
        onRun({
          ticker,
          lookback_days: Number(lookback),
          initial_capital: Number(capital),
          slippage_bps: Number(slippage),
        });
      }}
    >
      <div className="grid grid-cols-2 gap-3">
        <TextField label="Ticker" value={ticker} onChange={setTicker} />
        <NumField
          label="Lookback (days)"
          value={lookback}
          onChange={setLookback}
        />
        <NumField
          label="Initial capital ($)"
          value={capital}
          onChange={setCapital}
        />
        <NumField
          label="Slippage (bps)"
          value={slippage}
          onChange={setSlippage}
        />
      </div>
      <RunButton running={running} />
    </form>
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

function TextField({
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
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm font-mono"
        required
      />
    </label>
  );
}

function RunButton({ running }: { running: boolean }) {
  return (
    <button
      type="submit"
      disabled={running}
      className="mt-2 w-full rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:opacity-60"
    >
      {running ? "Running…" : "Run method"}
    </button>
  );
}

// --- Result panel -----------------------------------------------------------

function LabResult({ response }: { response: LabRunResponse }) {
  const r = response.result;
  return (
    <div className="space-y-4 text-xs">
      <div className="flex items-baseline justify-between gap-2">
        <div className="font-semibold text-zinc-900">{r.method_name}</div>
        <div className="font-mono text-[10px] text-zinc-500">
          {r.duration_ms.toFixed(1)} ms
        </div>
      </div>

      {!r.succeeded && (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-rose-800">
          <div className="font-semibold">Method failed</div>
          {r.error && <pre className="mt-1 whitespace-pre-wrap">{r.error}</pre>}
        </div>
      )}

      {r.succeeded && <PayloadRender payload={r.payload} />}

      <details className="rounded-md border border-zinc-200 bg-zinc-50 p-2">
        <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
          Raw JSON
        </summary>
        <pre className="mt-2 overflow-x-auto font-mono text-[10px] text-zinc-700">
          {JSON.stringify(r.payload, null, 2)}
        </pre>
      </details>
    </div>
  );
}

function PayloadRender({
  payload,
}: {
  payload: LabRunResponse["result"]["payload"];
}) {
  if (payload.kind === "options_price") {
    return <OptionsPayload p={payload} />;
  }
  if (payload.kind === "var") {
    return <VarPayloadView p={payload} />;
  }
  if (payload.kind === "portfolio") {
    return <PortfolioPayloadView p={payload} />;
  }
  if (payload.kind === "backtest") {
    return <BacktestPayloadView p={payload} />;
  }
  return null;
}

function OptionsPayload({ p }: { p: OptionsPriceResult }) {
  return (
    <div className="space-y-2">
      <Stat label="Price" value={`$${p.price.toFixed(4)}`} />
      {p.greeks && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          <Stat label="Delta" value={p.greeks.delta.toFixed(4)} />
          <Stat label="Gamma" value={p.greeks.gamma.toFixed(5)} />
          <Stat label="Vega" value={p.greeks.vega.toFixed(4)} />
          <Stat label="Theta" value={p.greeks.theta.toFixed(4)} />
          <Stat label="Rho" value={p.greeks.rho.toFixed(4)} />
        </div>
      )}
    </div>
  );
}

function VarPayloadView({ p }: { p: VaRPayload }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <Stat label="VaR loss" value={`$${p.var_loss.toFixed(2)}`} />
      <Stat label="CVaR loss" value={`$${p.cvar_loss.toFixed(2)}`} />
      <Stat label="N observations" value={String(p.n_observations)} />
      <Stat label="Mean return" value={p.mean_return.toExponential(2)} />
      <Stat label="Volatility" value={`${(p.volatility * 100).toFixed(2)}%`} />
    </div>
  );
}

function PortfolioPayloadView({ p }: { p: PortfolioPayload }) {
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Stat label="Solver" value={p.solver_name} />
        <Stat label="Sharpe" value={p.sharpe_ratio.toFixed(3)} />
        <Stat
          label="Volatility"
          value={`${(p.volatility_annualised * 100).toFixed(2)}%`}
        />
      </div>
      <div>
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
          Weights
        </div>
        <div className="space-y-1">
          {p.weights.map((w) => (
            <div
              key={w.ticker}
              className="flex items-center justify-between rounded-md border border-zinc-200 px-2 py-1 font-mono text-xs"
            >
              <span>{w.ticker}</span>
              <span>{(w.weight * 100).toFixed(2)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function BacktestPayloadView({ p }: { p: BacktestPayload }) {
  const m = p.metrics;
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <Stat
        label="Total return"
        value={`${(m.total_return * 100).toFixed(2)}%`}
      />
      <Stat label="Sharpe" value={m.sharpe_ratio.toFixed(2)} />
      <Stat label="Max DD" value={`${(m.max_drawdown * 100).toFixed(2)}%`} />
      <Stat label="# trades" value={String(m.n_trades)} />
      <Stat label="Win rate" value={`${(m.win_rate * 100).toFixed(1)}%`} />
      <Stat label="Calmar" value={m.calmar_ratio.toFixed(2)} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-zinc-500">
        {label}
      </div>
      <div className="font-mono text-xs text-zinc-900">{value}</div>
    </div>
  );
}
