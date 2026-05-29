"use client";

/**
 * Verification trace drawer — slide-out panel that shows the full pipeline
 * as a vertical timeline of stages. Triggered by clicking "Show full trace"
 * on any result card; also the surface Phase 7's "show working" link uses
 * to surface the verification engine on demand.
 *
 * Six stages, mirroring the backend audit log:
 *   1. Data ingestion
 *   2. Per-method calculation
 *   3. Cross-method check
 *   4. Invariants per method
 *   5. Sensitivity (portfolio only; collapsed otherwise)
 *   6. Final verdict
 *
 * Data comes entirely from `FinalAnswer` — no extra API call required. Every
 * fact shown traces back to a structured field, not free-text.
 */

import * as Dialog from "@radix-ui/react-dialog";
import type { FinalAnswer, PerMethodStatus } from "@/lib/types";

interface Props {
  open: boolean;
  onClose: () => void;
  answer: FinalAnswer;
  /** Optional method_id to scroll/highlight initially (when opened from a
   *  scorecard row click). */
  focusMethodId?: string | null;
}

export function VerificationTraceDrawer({
  open,
  onClose,
  answer,
  focusMethodId,
}: Props) {
  const v = answer.verification;
  const cross = v.cross_method;
  const rows = v.per_method_status;
  const allInvariantsPassed = v.invariants.every((i) => i.passed);

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (!o) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed right-0 top-0 z-50 flex h-screen w-[min(100vw,520px)] flex-col overflow-y-auto border-l border-zinc-200 bg-white shadow-xl">
          <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-zinc-200 bg-white p-4 sm:p-5">
            <div>
              <Dialog.Title className="text-sm font-semibold text-zinc-900">
                Verification trace
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-xs text-zinc-500">
                Every stage of how this answer was computed and checked.
              </Dialog.Description>
            </div>
            <Dialog.Close
              className="-mr-2 -mt-1 inline-flex h-11 w-11 items-center justify-center rounded-md text-2xl leading-none text-zinc-500 transition hover:bg-zinc-100"
              aria-label="Close trace"
            >
              ×
            </Dialog.Close>
          </header>

          <div className="space-y-4 p-4 sm:p-5">
            <Stage
              n={1}
              title="Data ingestion"
              passed
              subtitle={`Family: ${answer.family}`}
            >
              <p className="text-zinc-600">
                Request entered the pipeline as a structured payload.
                {rows.some((r) => r.duration_ms !== null) && (
                  <>
                    {" "}
                    First calculation slice ran in{" "}
                    <span className="font-mono">
                      {minDuration(rows).toFixed(1)}–
                      {maxDuration(rows).toFixed(1)} ms
                    </span>
                    .
                  </>
                )}
              </p>
            </Stage>

            <Stage
              n={2}
              title="Per-method calculation"
              passed={rows.every((r) => r.ran)}
              subtitle={`${rows.filter((r) => r.ran).length}/${rows.length} methods succeeded`}
            >
              <ul className="space-y-1">
                {rows.map((r) => (
                  <li
                    key={r.method_id}
                    className={`flex items-center justify-between rounded-md border px-2 py-1.5 text-xs ${
                      r.method_id === focusMethodId
                        ? "border-indigo-300 bg-indigo-50"
                        : "border-zinc-200"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          r.ran ? "bg-emerald-500" : "bg-rose-500"
                        }`}
                      />
                      <span className="text-zinc-800">{r.method_name}</span>
                    </span>
                    <span className="font-mono text-[11px] text-zinc-500">
                      {r.duration_ms !== null
                        ? `${r.duration_ms.toFixed(1)}ms`
                        : "—"}
                    </span>
                  </li>
                ))}
              </ul>
            </Stage>

            <Stage
              n={3}
              title="Cross-method check"
              passed={cross === null ? null : cross.passed}
              subtitle={
                cross
                  ? `${cross.methods_compared.length} methods compared`
                  : "Skipped — fewer than 2 headline methods"
              }
            >
              {cross ? (
                <div className="space-y-1 text-zinc-700">
                  <div>
                    Headline methods:{" "}
                    <span className="font-mono text-[11px]">
                      {cross.methods_compared.join(", ")}
                    </span>
                  </div>
                  <div>
                    Max absolute Δ:{" "}
                    <span className="font-mono">
                      {cross.max_absolute_delta.toExponential(2)}
                    </span>
                  </div>
                  <div>
                    Max relative Δ:{" "}
                    <span className="font-mono">
                      {cross.max_relative_delta.toExponential(2)}
                    </span>
                  </div>
                  <div>
                    Tolerance:{" "}
                    <span className="font-mono">
                      {cross.tolerance.toExponential(2)}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-zinc-600">
                  Only one method participated in the headline cross-check.
                  Verdict downgraded to partial.
                </p>
              )}
            </Stage>

            <Stage
              n={4}
              title="Invariants"
              passed={allInvariantsPassed}
              subtitle={`${v.invariants.filter((i) => i.passed).length}/${v.invariants.length} passed`}
            >
              <ul className="space-y-1">
                {v.invariants.map((inv) => (
                  <li key={inv.name} className="flex items-start gap-2">
                    <span
                      className={`mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
                        inv.passed ? "bg-emerald-500" : "bg-rose-500"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="font-mono text-[11px] text-zinc-800">
                        {inv.name}
                      </div>
                      <div className="text-[11px] text-zinc-500">
                        {inv.description}
                      </div>
                      {!inv.passed && inv.detail && (
                        <div className="mt-0.5 font-mono text-[10px] text-rose-700">
                          {inv.detail}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </Stage>

            {answer.family === "portfolio_optimization" && (
              <Stage
                n={5}
                title="Sensitivity"
                passed={
                  rows.find((r) => r.sensitivity_passed !== null)
                    ?.sensitivity_passed ?? null
                }
                subtitle={`Stability score ${(v.numerical_stability_score * 100).toFixed(0)}%`}
              >
                <p className="text-zinc-600">
                  Inputs perturbed ±1%; weights re-optimised and compared to the
                  primary solution.
                </p>
              </Stage>
            )}

            <Stage
              n={answer.family === "portfolio_optimization" ? 6 : 5}
              title="Final verdict"
              passed={v.overall_status === "verified"}
              subtitle={v.overall_status.replace("_", " ")}
            >
              <div className="space-y-1 text-zinc-700">
                <ScoreRow
                  label="Method agreement"
                  value={v.method_agreement_score}
                />
                <ScoreRow label="Bounds check" value={v.bounds_check_score} />
                <ScoreRow label="Input quality" value={v.input_quality_score} />
                <ScoreRow
                  label="Numerical stability"
                  value={v.numerical_stability_score}
                />
              </div>
            </Stage>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Stage({
  n,
  title,
  subtitle,
  passed,
  children,
}: {
  n: number;
  title: string;
  subtitle?: string;
  /** null = neutral (not applicable / skipped) */
  passed: boolean | null;
  children: React.ReactNode;
}) {
  const color =
    passed === true
      ? "border-emerald-200 bg-emerald-50"
      : passed === false
        ? "border-rose-200 bg-rose-50"
        : "border-zinc-200 bg-zinc-50";

  return (
    <section className={`rounded-lg border p-3 ${color}`}>
      <div className="mb-1 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-zinc-900 text-[10px] font-bold text-white">
            {n}
          </span>
          <h3 className="text-xs font-semibold text-zinc-900">{title}</h3>
        </div>
        {subtitle && (
          <span className="text-[11px] text-zinc-500">{subtitle}</span>
        )}
      </div>
      <div className="text-xs">{children}</div>
    </section>
  );
}

function ScoreRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span>{label}</span>
      <span className="font-mono">{(value * 100).toFixed(0)}%</span>
    </div>
  );
}

function minDuration(rows: PerMethodStatus[]): number {
  const ds = rows
    .map((r) => r.duration_ms)
    .filter((d): d is number => d !== null);
  return ds.length > 0 ? Math.min(...ds) : 0;
}

function maxDuration(rows: PerMethodStatus[]): number {
  const ds = rows
    .map((r) => r.duration_ms)
    .filter((d): d is number => d !== null);
  return ds.length > 0 ? Math.max(...ds) : 0;
}
