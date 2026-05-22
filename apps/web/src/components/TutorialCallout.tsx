"use client";

import type { ReactNode } from "react";

interface CalloutProps {
  n: number;
  children?: ReactNode;
  /** Override colour. Defaults to indigo. */
  tone?: "indigo" | "emerald" | "rose" | "amber";
}

const TONE_CLASSES: Record<NonNullable<CalloutProps["tone"]>, string> = {
  indigo: "bg-indigo-600 text-white ring-2 ring-indigo-100",
  emerald: "bg-emerald-600 text-white ring-2 ring-emerald-100",
  rose: "bg-rose-600 text-white ring-2 ring-rose-100",
  amber: "bg-amber-500 text-white ring-2 ring-amber-100",
};

/** Numbered marker rendered inline next to a value. The matching number in
 *  the surrounding `<CalloutLegend>` explains what it means. */
export function Callout({ n, tone = "indigo", children }: CalloutProps) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${TONE_CLASSES[tone]}`}
        aria-label={`Callout ${n}`}
      >
        {n}
      </span>
      {children}
    </span>
  );
}

export interface CalloutItem {
  n: number;
  tone?: NonNullable<CalloutProps["tone"]>;
  title: string;
  body: ReactNode;
}

interface LegendProps {
  items: CalloutItem[];
}

export function CalloutLegend({ items }: LegendProps) {
  return (
    <ol className="space-y-2">
      {items.map((item) => (
        <li key={item.n} className="flex gap-3 text-xs leading-relaxed">
          <Callout n={item.n} tone={item.tone} />
          <div>
            <div className="font-semibold text-zinc-900">{item.title}</div>
            <div className="mt-0.5 text-zinc-700">{item.body}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}
