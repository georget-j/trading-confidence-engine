"use client";

/**
 * Per-method scorecard — one compact row per calculator showing whether it
 * ran, what value it produced, whether it agreed with the headline pair,
 * and which invariants its own payload satisfied.
 *
 * Replaces the "Cross-method check" block on every result card. The row data
 * comes from `verification.per_method_status` (Slice 5f). Methods marked
 * `n/a` for agreement still appear — they ran successfully but weren't part
 * of the headline cross-check (e.g. Monte Carlo + Crank-Nicolson on the
 * options tab; only the BSM/binomial pair gates the verdict).
 */

import type { PerMethodStatus } from "@/lib/types";

interface Props {
  per_method_status: PerMethodStatus[];
  /** Optional pretty-print for the comparable value (e.g. "$9.94" or "$1,432.00"). */
  valueFormatter?: (v: number) => string;
  /** Optional click handler — turns each row into a button that opens the
   *  verification trace drawer focused on that method. */
  onMethodClick?: (method_id: string) => void;
}

export function MethodScorecard({
  per_method_status: rows,
  valueFormatter,
  onMethodClick,
}: Props) {
  if (rows.length === 0) {
    return (
      <div className="text-xs text-zinc-500">
        Per-method scorecard not available for this result.
      </div>
    );
  }
  const fmt = valueFormatter ?? defaultFmt;

  return (
    <div className="space-y-1.5">
      {rows.map((r) => (
        <ScorecardRow
          key={r.method_id}
          row={r}
          fmt={fmt}
          onClick={onMethodClick ? () => onMethodClick(r.method_id) : undefined}
        />
      ))}
    </div>
  );
}

function ScorecardRow({
  row,
  fmt,
  onClick,
}: {
  row: PerMethodStatus;
  fmt: (v: number) => string;
  onClick?: () => void;
}) {
  const invariantCount =
    row.invariants_passed.length + row.invariants_failed.length;
  const invariantPart =
    invariantCount > 0
      ? `${row.invariants_passed.length}/${invariantCount} invariants`
      : "n/a";

  const baseCls = `flex flex-col gap-1 rounded-md border px-3 py-2 text-xs sm:flex-row sm:items-center sm:justify-between sm:gap-3 ${rowBorder(
    row,
  )}`;
  const body = (
    <>
      <div className="flex min-w-0 items-center gap-2">
        <StatusDot row={row} />
        <span className="truncate text-zinc-800">{row.method_name}</span>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 font-mono text-zinc-600 sm:justify-end">
        <span className="font-semibold text-zinc-900">
          {row.ran && row.value !== null ? fmt(row.value) : "—"}
        </span>
        <AgreementLabel row={row} />
        <span title={invariantTooltip(row)} className="cursor-help">
          {invariantPart}
        </span>
        {row.sensitivity_passed !== null && (
          <span
            className={
              row.sensitivity_passed ? "text-emerald-700" : "text-amber-700"
            }
            title="Sensitivity / stability check"
          >
            {row.sensitivity_passed ? "stable" : "fragile"}
          </span>
        )}
        {row.duration_ms !== null && (
          <span className="text-[10px] text-zinc-400">
            {row.duration_ms.toFixed(1)}ms
          </span>
        )}
      </div>
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`${baseCls} w-full text-left transition hover:ring-1 hover:ring-zinc-400`}
        title="Open verification trace for this method"
      >
        {body}
      </button>
    );
  }
  return <div className={baseCls}>{body}</div>;
}

function StatusDot({ row }: { row: PerMethodStatus }) {
  if (!row.ran) {
    return (
      <span
        className="h-2 w-2 shrink-0 rounded-full bg-rose-500"
        title={row.error ?? "Method failed"}
      />
    );
  }
  if (row.invariants_failed.length > 0) {
    return (
      <span
        className="h-2 w-2 shrink-0 rounded-full bg-rose-500"
        title="Invariant violation"
      />
    );
  }
  if (row.agreement_status === "diverges") {
    return (
      <span
        className="h-2 w-2 shrink-0 rounded-full bg-amber-500"
        title="Diverges from headline cross-check"
      />
    );
  }
  return (
    <span
      className="h-2 w-2 shrink-0 rounded-full bg-emerald-500"
      title="Passes headline checks"
    />
  );
}

function AgreementLabel({ row }: { row: PerMethodStatus }) {
  if (!row.ran) {
    return <span className="text-rose-700">FAILED</span>;
  }
  if (row.agreement_status === "agrees") {
    return <span className="text-emerald-700">agrees</span>;
  }
  if (row.agreement_status === "diverges") {
    return (
      <span
        className="text-amber-700"
        title={`Diverges vs ${row.divergent_against.join(", ")}`}
      >
        diverges
      </span>
    );
  }
  return <span className="text-zinc-500">n/a</span>;
}

function rowBorder(row: PerMethodStatus): string {
  if (!row.ran || row.invariants_failed.length > 0)
    return "border-rose-200 bg-rose-50";
  if (row.agreement_status === "diverges")
    return "border-amber-200 bg-amber-50";
  return "border-zinc-200 bg-white";
}

function invariantTooltip(row: PerMethodStatus): string {
  const parts: string[] = [];
  if (row.invariants_passed.length > 0) {
    parts.push(`Passed: ${row.invariants_passed.join(", ")}`);
  }
  if (row.invariants_failed.length > 0) {
    parts.push(`Failed: ${row.invariants_failed.join(", ")}`);
  }
  return parts.join("\n");
}

function defaultFmt(v: number): string {
  if (Math.abs(v) >= 1000) return v.toFixed(2);
  if (Math.abs(v) >= 1) return v.toFixed(4);
  return v.toExponential(3);
}
