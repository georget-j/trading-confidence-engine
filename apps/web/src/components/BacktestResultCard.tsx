import type {
  BacktestPayload,
  BacktestRequest,
  FinalAnswer,
} from "@/lib/types";
import { ConfidenceBreakdown } from "./ConfidenceBreakdown";
import { EquityCurveChart } from "./EquityCurveChart";
import { SaveButton } from "./SaveButton";
import { VerificationBadge } from "./VerificationBadge";
import { WhyPartialExpander } from "./WhyPartialExpander";

interface Props {
  answer: FinalAnswer;
  initialCapital: number;
  request?: BacktestRequest;
}

function isBacktestPayload(
  p: FinalAnswer["primary_result"],
): p is BacktestPayload {
  return p.kind === "backtest";
}

const FMT_PCT = (v: number, digits: number = 2) =>
  `${(v * 100).toFixed(digits)}%`;

const STRATEGY_LABEL: Record<string, string> = {
  buy_and_hold: "Buy & hold",
  ma_crossover: "Moving-average crossover",
  momentum: "Momentum",
};

export function BacktestResultCard({ answer, initialCapital, request }: Props) {
  if (!isBacktestPayload(answer.primary_result)) {
    return (
      <div className="text-sm text-rose-700">
        Unexpected payload — expected backtest.
      </div>
    );
  }
  const p = answer.primary_result;
  const m = p.metrics;
  const bench = p.benchmark_metrics;
  const alpha = bench ? m.total_return - bench.total_return : null;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-zinc-500">
            {STRATEGY_LABEL[p.strategy] ?? p.strategy} · {p.ticker}
          </div>
          <div className="mt-1 flex items-baseline gap-4">
            <div>
              <div className="text-[10px] text-zinc-500">Total return</div>
              <div
                className={`font-mono text-2xl font-semibold ${
                  m.total_return >= 0 ? "text-emerald-700" : "text-rose-700"
                }`}
              >
                {m.total_return >= 0 ? "+" : ""}
                {FMT_PCT(m.total_return)}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-zinc-500">Sharpe</div>
              <div className="font-mono text-2xl font-semibold text-zinc-900">
                {m.sharpe_ratio.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-zinc-500">Max DD</div>
              <div className="font-mono text-2xl font-semibold text-rose-700">
                −{FMT_PCT(m.max_drawdown)}
              </div>
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <VerificationBadge status={answer.verification_status} />
          {request && (
            <SaveButton
              family="backtest"
              payload={request}
              defaultLabel={`${request.ticker} · ${STRATEGY_LABEL[p.strategy] ?? p.strategy}`}
              summary={`${answer.verification_status} · ${(m.total_return * 100).toFixed(1)}%`}
            />
          )}
        </div>
      </div>

      <p className="text-sm leading-relaxed text-zinc-700">
        {answer.explanation}
      </p>

      <WhyPartialExpander
        status={answer.verification_status}
        verification={answer.verification}
        calculatorResults={answer.calculator_results}
        family="var"
      />

      <ConfidenceBreakdown verification={answer.verification} />

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Equity curve
        </div>
        <div className="mt-2">
          <EquityCurveChart
            curve={p.equity_curve}
            initialCapital={initialCapital}
          />
        </div>
      </div>

      {bench && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
            vs buy-and-hold benchmark
          </div>
          <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
            <BenchStat
              label="Strategy"
              total={m.total_return}
              sharpe={m.sharpe_ratio}
              dd={m.max_drawdown}
            />
            <BenchStat
              label="Buy & hold"
              total={bench.total_return}
              sharpe={bench.sharpe_ratio}
              dd={bench.max_drawdown}
            />
            <div className="rounded-md border border-zinc-200 p-2">
              <div className="text-[10px] text-zinc-500">Alpha (return)</div>
              <div
                className={`font-mono ${
                  alpha !== null && alpha >= 0
                    ? "text-emerald-700"
                    : "text-rose-700"
                }`}
              >
                {alpha !== null
                  ? `${alpha >= 0 ? "+" : ""}${FMT_PCT(alpha)}`
                  : "—"}
              </div>
              <div className="mt-1 text-[10px] text-zinc-500">
                Extra return over passively holding the underlying.
              </div>
            </div>
          </div>
        </div>
      )}

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Slippage sensitivity
        </div>
        <div className="mt-2 rounded-lg border border-zinc-200 p-3 text-xs">
          <div className="grid grid-cols-5 gap-2">
            {p.slippage_sensitivity.bps.map((bp, i) => (
              <div key={bp} className="text-center">
                <div className="text-[10px] text-zinc-500">{bp}bp</div>
                <div
                  className={`font-mono ${
                    p.slippage_sensitivity.total_return[i] >= 0
                      ? "text-emerald-700"
                      : "text-rose-700"
                  }`}
                >
                  {p.slippage_sensitivity.total_return[i] >= 0 ? "+" : ""}
                  {FMT_PCT(p.slippage_sensitivity.total_return[i], 1)}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-2 text-zinc-600">
            Total return under different per-trade slippage assumptions. A steep
            drop means most of the strategy&apos;s headline number is consumed
            by trading frictions.
          </p>
        </div>
      </div>

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Verification flags
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
          <FlagBox
            label="Walk-forward reproducible"
            passed={p.walk_forward_reproducible}
            description="Running the backtest twice produces bit-identical equity curves."
          />
          <FlagBox
            label="No look-ahead bias"
            passed={p.lookahead_clean}
            description="Positions don't correlate with future returns more than with current ones."
          />
        </div>
      </div>

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Other stats
        </div>
        <div className="mt-2 grid grid-cols-4 gap-2 text-xs">
          <Stat label="Ann. return" value={FMT_PCT(m.annualised_return)} />
          <Stat label="Ann. vol" value={FMT_PCT(m.annualised_volatility)} />
          <Stat label="Calmar" value={m.calmar_ratio.toFixed(2)} />
          <Stat label="Trades" value={String(m.n_trades)} />
          <Stat label="Win rate" value={FMT_PCT(m.win_rate, 1)} />
        </div>
      </div>

      {answer.limitations.length > 0 && (
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
          <div className="font-semibold text-zinc-700">Limitations</div>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {answer.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function BenchStat({
  label,
  total,
  sharpe,
  dd,
}: {
  label: string;
  total: number;
  sharpe: number;
  dd: number;
}) {
  return (
    <div className="rounded-md border border-zinc-200 p-2">
      <div className="text-[10px] text-zinc-500">{label}</div>
      <div className="space-y-0.5 font-mono">
        <div className={total >= 0 ? "text-emerald-700" : "text-rose-700"}>
          {total >= 0 ? "+" : ""}
          {(total * 100).toFixed(2)}%
        </div>
        <div className="text-[10px] text-zinc-600">Sh {sharpe.toFixed(2)}</div>
        <div className="text-[10px] text-zinc-600">
          DD {(dd * 100).toFixed(1)}%
        </div>
      </div>
    </div>
  );
}

function FlagBox({
  label,
  passed,
  description,
}: {
  label: string;
  passed: boolean;
  description: string;
}) {
  return (
    <div
      className={`rounded-md border p-2 ${
        passed
          ? "border-emerald-200 bg-emerald-50"
          : "border-rose-200 bg-rose-50"
      }`}
    >
      <div className="flex items-center gap-1.5">
        <span
          className={`h-2 w-2 rounded-full ${
            passed ? "bg-emerald-500" : "bg-rose-500"
          }`}
        />
        <span
          className={`text-xs font-semibold ${
            passed ? "text-emerald-900" : "text-rose-900"
          }`}
        >
          {label}
        </span>
      </div>
      <p className="mt-1 text-[10px] text-zinc-700">{description}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 px-2 py-1.5">
      <div className="text-[10px] text-zinc-500">{label}</div>
      <div className="font-mono text-xs text-zinc-900">{value}</div>
    </div>
  );
}
