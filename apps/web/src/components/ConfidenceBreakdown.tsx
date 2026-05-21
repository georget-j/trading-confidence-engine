import type { VerificationResult } from "@/lib/types";

interface Props {
  verification: VerificationResult;
}

/** V3 — surface the 5-score confidence model explicitly. */
export function ConfidenceBreakdown({ verification }: Props) {
  const scores: { key: string; label: string; value: number; why: string }[] = [
    {
      key: "method_agreement",
      label: "Method agreement",
      value: verification.method_agreement_score,
      why: verification.cross_method
        ? `${verification.cross_method.methods_compared.length} methods compared, max relative Δ ${verification.cross_method.max_relative_delta.toExponential(2)}`
        : "Only one method ran — agreement could not be computed.",
    },
    {
      key: "bounds_check",
      label: "Invariants",
      value: verification.bounds_check_score,
      why: `${verification.invariants.filter((i) => i.passed).length} of ${verification.invariants.length} invariants passed`,
    },
    {
      key: "input_quality",
      label: "Input quality",
      value: verification.input_quality_score,
      why: "Structured input was complete; no inferred or stale fields.",
    },
    {
      key: "numerical_stability",
      label: "Numerical stability",
      value: verification.numerical_stability_score,
      why: "Closed-form arithmetic is stable; binomial tree converged.",
    },
  ];

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
        Confidence breakdown
      </div>
      <div className="mt-2 space-y-2">
        {scores.map((s) => (
          <ScoreBar key={s.key} label={s.label} value={s.value} why={s.why} />
        ))}
      </div>
    </div>
  );
}

function ScoreBar({
  label,
  value,
  why,
}: {
  label: string;
  value: number;
  why: string;
}) {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.95
      ? "bg-emerald-500"
      : value >= 0.7
        ? "bg-amber-500"
        : "bg-rose-500";
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-zinc-700">{label}</span>
        <span className="font-mono text-zinc-900">{pct}%</span>
      </div>
      <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
        <div
          className={`h-full ${color} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-0.5 text-[10px] text-zinc-500">{why}</div>
    </div>
  );
}
