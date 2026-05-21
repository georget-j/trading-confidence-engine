import type { FinalAnswer, VaRPayload } from "@/lib/types";
import { ConfidenceBreakdown } from "./ConfidenceBreakdown";
import { VerificationBadge } from "./VerificationBadge";

interface Props {
  answer: FinalAnswer;
}

function isVaRPayload(p: FinalAnswer["primary_result"]): p is VaRPayload {
  return p.kind === "var";
}

const FMT_USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

export function RiskResultCard({ answer }: Props) {
  if (!isVaRPayload(answer.primary_result)) {
    return (
      <div className="text-sm text-rose-700">
        Unexpected payload type — expected VaR.
      </div>
    );
  }
  const primary = answer.primary_result;
  const cross = answer.verification.cross_method;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-zinc-500">
            Value at Risk
          </div>
          <div className="mt-1 font-mono text-4xl font-semibold text-rose-700">
            −{FMT_USD.format(primary.var_loss)}
          </div>
          <div className="mt-0.5 text-xs text-zinc-600">
            Expected shortfall (CVaR):{" "}
            <span className="font-mono text-zinc-900">
              −{FMT_USD.format(primary.cvar_loss)}
            </span>
          </div>
        </div>
        <VerificationBadge status={answer.verification_status} />
      </div>

      <p className="text-sm leading-relaxed text-zinc-700">
        {answer.explanation}
      </p>

      <ConfidenceBreakdown verification={answer.verification} />

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Method comparison
        </div>
        {cross && (
          <div className="mt-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-600">
                {cross.methods_compared.length} methods · max relative Δ{" "}
                {(cross.max_relative_delta * 100).toFixed(2)}%
              </span>
              <span
                className={
                  cross.passed
                    ? "font-semibold text-emerald-700"
                    : "font-semibold text-rose-700"
                }
              >
                {cross.passed ? "within tolerance" : "DIVERGENT"}
              </span>
            </div>
          </div>
        )}
        <div className="mt-2 space-y-1">
          {answer.calculator_results.map((c) => {
            const isVar = c.payload.kind === "var";
            const varLoss = isVar ? (c.payload as VaRPayload).var_loss : 0;
            const cvarLoss = isVar ? (c.payload as VaRPayload).cvar_loss : 0;
            return (
              <div
                key={c.calculator_id}
                className="flex items-center justify-between rounded-md border border-zinc-200 px-3 py-2 text-xs"
              >
                <span className="text-zinc-700">{c.method_name}</span>
                <span className="font-mono">
                  {c.succeeded ? (
                    <>
                      <span className="font-semibold text-zinc-900">
                        VaR {FMT_USD.format(varLoss)}
                      </span>
                      <span className="ml-2 text-zinc-500">
                        CVaR {FMT_USD.format(cvarLoss)}
                      </span>
                      <span className="ml-2 text-zinc-400">
                        {c.duration_ms.toFixed(0)}ms
                      </span>
                    </>
                  ) : (
                    <span className="font-semibold text-rose-700">FAILED</span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Sample stats
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
          <Stat label="N observations" value={String(primary.n_observations)} />
          <Stat
            label="Mean return"
            value={`${(primary.mean_return * 100).toFixed(3)}%`}
          />
          <Stat
            label="Volatility"
            value={`${(primary.volatility * 100).toFixed(2)}%`}
          />
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 px-2 py-1.5">
      <div className="text-[10px] text-zinc-500">{label}</div>
      <div className="font-mono text-xs text-zinc-900">{value}</div>
    </div>
  );
}
