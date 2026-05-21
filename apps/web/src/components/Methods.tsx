"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";
import { listMethods } from "@/lib/api";
import type { Cost, MethodEntry } from "@/lib/types";

const FAMILY_LABELS: Record<string, string> = {
  options_pricing: "Options",
  risk_metrics: "Risk (VaR)",
  portfolio_optimization: "Portfolio",
  backtest: "Backtest",
};

const COST_LABELS: Record<Cost, string> = {
  negligible: "<1ms",
  cheap: "<100ms",
  moderate: "<1s",
  expensive: ">1s",
};

const COST_CHIP: Record<Cost, string> = {
  negligible: "bg-emerald-100 text-emerald-800",
  cheap: "bg-sky-100 text-sky-800",
  moderate: "bg-amber-100 text-amber-800",
  expensive: "bg-rose-100 text-rose-800",
};

export function Methods() {
  const [open, setOpen] = useState(false);
  const [methods, setMethods] = useState<MethodEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || methods !== null) return;
    listMethods()
      .then(setMethods)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [open, methods]);

  // Group by family for the sidebar.
  const grouped = methods
    ? methods.reduce<Record<string, MethodEntry[]>>((acc, m) => {
        (acc[m.family] ??= []).push(m);
        return acc;
      }, {})
    : {};

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className="text-xs font-medium text-zinc-600 transition hover:text-zinc-900"
        >
          Methods
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[88vh] w-[95vw] max-w-4xl -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl bg-white p-6 shadow-xl">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-base font-semibold text-zinc-900">
                Verified methods
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-xs text-zinc-600">
                Every calculator the engine runs, the assumptions it makes, the
                math identities it checks, and what cross-verifies it.
              </Dialog.Description>
            </div>
            <Dialog.Close
              className="rounded-md p-1 text-zinc-500 transition hover:bg-zinc-100"
              aria-label="Close"
            >
              ×
            </Dialog.Close>
          </div>

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              {error}
            </div>
          )}

          {!methods && !error && (
            <div className="py-8 text-center text-sm text-zinc-500">
              Loading…
            </div>
          )}

          {methods && (
            <div className="flex-1 overflow-y-auto pr-1">
              {Object.entries(grouped).map(([family, entries]) => (
                <section key={family} className="mb-6">
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    {FAMILY_LABELS[family] ?? family}
                  </h3>
                  <div className="space-y-3">
                    {entries.map((m) => (
                      <MethodCard key={m.calculator_id} method={m} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function MethodCard({ method }: { method: MethodEntry }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-zinc-900">
            {method.method_name}
          </div>
          <div className="mt-0.5 font-mono text-[10px] text-zinc-500">
            {method.calculator_id}
          </div>
        </div>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
            COST_CHIP[method.cost]
          }`}
        >
          {COST_LABELS[method.cost]}
        </span>
      </div>

      <p className="mt-2 text-sm leading-relaxed text-zinc-700">
        {method.one_line}
      </p>

      <details className="mt-2">
        <summary className="cursor-pointer text-xs font-medium text-zinc-600 hover:text-zinc-900">
          More detail
        </summary>
        <div className="mt-2 space-y-3 text-xs text-zinc-700">
          <p className="leading-relaxed">{method.long_description}</p>

          <BulletList title="Inputs required" items={method.inputs_required} />
          <BulletList
            title="Works well when"
            items={method.domain_of_validity}
          />
          <BulletList
            title="Breaks or is biased when"
            items={method.domain_limits}
            color="rose"
          />
          <BulletList
            title="Invariants checked"
            items={method.invariants_checked}
            color="emerald"
          />

          {method.independent_methods.length > 0 && (
            <div>
              <div className="font-semibold text-zinc-900">
                Cross-verified by
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {method.independent_methods.map((id) => (
                  <span
                    key={id}
                    className="rounded bg-zinc-100 px-2 py-0.5 font-mono text-[10px] text-zinc-700"
                  >
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </details>
    </div>
  );
}

function BulletList({
  title,
  items,
  color,
}: {
  title: string;
  items: string[];
  color?: "rose" | "emerald";
}) {
  if (items.length === 0) return null;
  const bullet =
    color === "rose"
      ? "text-rose-600"
      : color === "emerald"
        ? "text-emerald-600"
        : "text-zinc-400";
  return (
    <div>
      <div className="font-semibold text-zinc-900">{title}</div>
      <ul className="mt-1 space-y-0.5">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span
              className={`mt-1 inline-block h-1 w-1 rounded-full ${bullet}`}
            />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
