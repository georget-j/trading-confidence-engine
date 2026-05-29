"use client";

/**
 * Placeholder card for the four trader-pivot tabs (Trade ideas, My portfolio,
 * Hedge finder, Compare) until Phases 7b–7e fill in real content.
 *
 * Each placeholder describes what the tab will do, lists the planned
 * feature set, and points the user at the Calculators tab where the
 * underlying verification machinery is already live and usable.
 */

import type { ReactNode } from "react";

interface Props {
  badge: string;
  title: string;
  whatItWillDo: ReactNode;
  features: string[];
  /** Optional callback to jump to the Calculators tab. */
  onOpenCalculators?: () => void;
  /** Optional related calculator hint shown on the CTA. */
  calculatorsHint?: string;
}

export function TraderPlaceholder({
  badge,
  title,
  whatItWillDo,
  features,
  onOpenCalculators,
  calculatorsHint,
}: Props) {
  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-4 shadow-sm sm:p-6">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-indigo-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
            {badge}
          </span>
          <h2 className="text-sm font-semibold text-zinc-900">{title}</h2>
        </div>
        <p className="mt-2 max-w-3xl text-xs leading-relaxed text-zinc-700 sm:text-sm">
          {whatItWillDo}
        </p>
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Coming in the trader-pivot rollout
        </div>
        <ul className="mt-3 space-y-2">
          {features.map((f) => (
            <li
              key={f}
              className="flex items-start gap-2 text-sm text-zinc-700"
            >
              <span className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500" />
              <span>{f}</span>
            </li>
          ))}
        </ul>

        {onOpenCalculators && (
          <div className="mt-5 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-700">
            <div className="font-semibold text-zinc-900">
              Want to use the engine right now?
            </div>
            <p className="mt-1">
              {calculatorsHint ??
                "The underlying calculators are already live in the Calculators tab. Cross-method verification, invariant checks, and the full trace drawer are all there."}
            </p>
            <button
              type="button"
              onClick={onOpenCalculators}
              className="mt-2 inline-flex items-center gap-1 rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-zinc-800"
            >
              Open Calculators →
            </button>
          </div>
        )}

        <p className="mt-4 text-[11px] text-zinc-500">
          Educational / informational use only — not investment advice. Any
          eventual recommendations will be historical-correlation-based and will
          carry their own per-recommendation disclaimer.
        </p>
      </section>
    </div>
  );
}
