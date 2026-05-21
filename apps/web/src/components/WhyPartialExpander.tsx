"use client";

import { useState } from "react";
import type {
  CalculatorResult,
  VerificationResult,
  VerificationStatus,
} from "@/lib/types";

interface Props {
  status: VerificationStatus;
  verification: VerificationResult;
  /** Original calculator outputs — used to surface the divergent method's name. */
  calculatorResults: CalculatorResult[];
  /** "options" or "var" — controls the family-specific copy. */
  family: "options" | "var";
}

/** Renders nothing when status === "verified". Otherwise expands into a
 *  context-aware plain-English explanation of *which* check slipped. */
export function WhyPartialExpander({
  status,
  verification,
  calculatorResults,
  family,
}: Props) {
  const [open, setOpen] = useState(true);

  if (status === "verified") return null;

  const reasons = buildReasons(status, verification, calculatorResults, family);

  const accent =
    status === "partially_verified"
      ? {
          border: "border-amber-300",
          bg: "bg-amber-50",
          heading: "text-amber-900",
        }
      : {
          border: "border-rose-300",
          bg: "bg-rose-50",
          heading: "text-rose-900",
        };

  return (
    <div className={`rounded-lg border ${accent.border} ${accent.bg} p-3`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between"
        aria-expanded={open}
      >
        <span className={`text-xs font-semibold ${accent.heading}`}>
          Why did this go{" "}
          {status === "partially_verified" ? "partial" : "not-verified"}?
        </span>
        <span className={`text-xs ${accent.heading}`}>{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="mt-2 space-y-2 text-xs leading-relaxed text-zinc-800">
          {reasons.map((r, i) => (
            <div key={i}>
              <div className="font-semibold text-zinc-900">{r.what}</div>
              <p className="mt-0.5 text-zinc-700">{r.why}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface Reason {
  what: string;
  why: string;
}

function buildReasons(
  status: VerificationStatus,
  verification: VerificationResult,
  results: CalculatorResult[],
  family: "options" | "var",
): Reason[] {
  const reasons: Reason[] = [];

  // 1. Invariants — hardest signal, always surface failures first.
  const failedInvariants = verification.invariants.filter((i) => !i.passed);
  if (failedInvariants.length > 0) {
    for (const inv of failedInvariants) {
      reasons.push({
        what: `Invariant failed: ${humanizeInvariant(inv.name)}`,
        why: `${inv.description}${inv.detail ? `. Detail: ${inv.detail}` : ""}. This is a hard mathematical identity — its failure means at least one of the calculators returned a number that breaks the rules of the model, so the engine refuses to call the result verified.`,
      });
    }
  }

  // 2. Cross-method divergence.
  const cross = verification.cross_method;
  if (cross !== null && !cross.passed) {
    reasons.push({
      what: `Methods disagreed by ${(cross.max_relative_delta * 100).toFixed(2)}%`,
      why:
        family === "var"
          ? "Historical, parametric, and Monte Carlo VaR diverged by more than the wide tolerance. On real-world equity data this almost always means returns have fat tails — extreme down-days happen more often than a normal distribution would predict — and the normal-assumption methods underestimate the risk."
          : "The two pricing methods (closed-form vs binomial) didn't agree within tolerance. This is rare for well-behaved European options; it usually points to extreme parameter combinations (very high vol, very short or very long expiry) where the binomial tree is at the edge of its convergence.",
    });
  } else if (
    cross !== null &&
    cross.passed &&
    verification.method_agreement_score < 1.0
  ) {
    reasons.push({
      what: `Methods agreed in the wider band, not the tight one (max Δ ${(cross.max_relative_delta * 100).toFixed(2)}%)`,
      why:
        family === "var"
          ? "The three VaR methods are close enough to be useful but not close enough to fully trust as a single number — typical of real-world data with mild non-normality. Historical is your most assumption-free estimate; treat parametric as an upper-vs-lower view, not a point."
          : "The two methods are close but not within the tightest tolerance. Use the result as a guide rather than a hard quote.",
    });
  }

  // 3. Only one successful method.
  const succeeded = results.filter((r) => r.succeeded);
  if (cross === null && succeeded.length < 2) {
    const failed = results.filter((r) => !r.succeeded);
    reasons.push({
      what: "Only one calculator returned a result",
      why: `Cross-method verification needs at least two successful methods. ${failed.length > 0 ? `Failures: ${failed.map((f) => `${f.method_name} (${f.error ?? "unknown"})`).join("; ")}.` : ""} Without a second opinion the engine can't promote this result above 'partially verified'.`,
    });
  }

  // 4. Input quality penalty.
  if (verification.input_quality_score < 0.8) {
    reasons.push({
      what: `Input quality is ${Math.round(verification.input_quality_score * 100)}%`,
      why: "Inputs were incomplete or stale. Even a perfectly verified calculation should be treated as approximate when the underlying data isn't fresh.",
    });
  }

  // Fallback if no specific reason was identified — shouldn't normally happen
  // for non-verified statuses, but better than an empty box.
  if (reasons.length === 0) {
    reasons.push({
      what: "Status did not reach 'verified'",
      why: "The engine couldn't promote this result to fully verified. Inspect the method comparison and invariants list above for specifics.",
    });
  }

  return reasons;
}

function humanizeInvariant(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b(var|cvar)\b/gi, (s) => s.toUpperCase());
}
