import type { FinalAnswer, OptionsPriceResult } from "@/lib/types";
import { ConfidenceBreakdown } from "./ConfidenceBreakdown";
import { VerificationBadge } from "./VerificationBadge";

interface Props {
  answer: FinalAnswer;
}

function isOptionsResult(
  p: FinalAnswer["primary_result"],
): p is OptionsPriceResult {
  return p.kind === "options_price";
}

export function ResultCard({ answer }: Props) {
  if (!isOptionsResult(answer.primary_result)) {
    return (
      <div className="text-sm text-rose-700">
        Unexpected payload — expected options pricing.
      </div>
    );
  }
  const primary = answer.primary_result;
  const greeks = primary.greeks;
  const cross = answer.verification.cross_method;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-zinc-500">
            Result
          </div>
          <div className="mt-1 font-mono text-4xl font-semibold text-zinc-900">
            ${primary.price.toFixed(4)}
          </div>
        </div>
        <VerificationBadge status={answer.verification_status} />
      </div>

      <p className="text-sm leading-relaxed text-zinc-700">
        {answer.explanation}
      </p>

      <ConfidenceBreakdown verification={answer.verification} />

      {greeks && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Greeks
          </div>
          <div className="mt-2 grid grid-cols-5 gap-2">
            <Stat label="Δ delta" value={greeks.delta} digits={4} />
            <Stat label="Γ gamma" value={greeks.gamma} digits={5} />
            <Stat label="ν vega" value={greeks.vega} digits={4} />
            <Stat label="Θ theta" value={greeks.theta} digits={4} />
            <Stat label="ρ rho" value={greeks.rho} digits={4} />
          </div>
        </div>
      )}

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Cross-method check
        </div>
        {cross ? (
          <div className="mt-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-600">
                {cross.methods_compared.length} methods compared
              </span>
              <span
                className={
                  cross.passed
                    ? "font-semibold text-emerald-700"
                    : "font-semibold text-rose-700"
                }
              >
                {cross.passed ? "agreement within tolerance" : "DISAGREEMENT"}
              </span>
            </div>
            <div className="mt-1 grid grid-cols-2 gap-2 font-mono text-zinc-700">
              <div>max Δ abs: {cross.max_absolute_delta.toExponential(2)}</div>
              <div>max Δ rel: {cross.max_relative_delta.toExponential(2)}</div>
            </div>
          </div>
        ) : (
          <div className="mt-2 text-xs text-zinc-500">
            Only one method available — cross-check skipped.
          </div>
        )}
        <div className="mt-2 space-y-1">
          {answer.calculator_results.map((c) => (
            <div
              key={c.calculator_id}
              className="flex items-center justify-between rounded-md border border-zinc-200 px-3 py-2 text-xs"
            >
              <span className="text-zinc-700">{c.method_name}</span>
              <span
                className={
                  c.succeeded
                    ? "font-mono font-semibold text-zinc-900"
                    : "font-mono font-semibold text-rose-700"
                }
              >
                {c.succeeded && c.payload.kind === "options_price"
                  ? `$${c.payload.price.toFixed(4)}`
                  : "FAILED"}
                <span className="ml-2 text-zinc-400">
                  {c.duration_ms.toFixed(1)}ms
                </span>
              </span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Invariants
        </div>
        <div className="mt-2 space-y-1">
          {answer.verification.invariants.map((inv) => (
            <div
              key={inv.name}
              className="flex items-center gap-2 text-xs text-zinc-600"
            >
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${
                  inv.passed ? "bg-emerald-500" : "bg-rose-500"
                }`}
              />
              <span className="font-mono">{inv.name}</span>
              {!inv.passed && inv.detail && (
                <span className="ml-2 text-rose-700">{inv.detail}</span>
              )}
            </div>
          ))}
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

function Stat({
  label,
  value,
  digits,
}: {
  label: string;
  value: number;
  digits: number;
}) {
  return (
    <div className="rounded-md border border-zinc-200 px-2 py-1.5">
      <div className="text-[10px] text-zinc-500">{label}</div>
      <div className="font-mono text-xs text-zinc-900">
        {value.toFixed(digits)}
      </div>
    </div>
  );
}
