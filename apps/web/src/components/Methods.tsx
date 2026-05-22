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

const FAMILY_ORDER = [
  "options_pricing",
  "risk_metrics",
  "portfolio_optimization",
  "backtest",
];

const FAMILY_ACCENT: Record<string, string> = {
  options_pricing: "bg-sky-50 border-sky-200",
  risk_metrics: "bg-rose-50 border-rose-200",
  portfolio_optimization: "bg-emerald-50 border-emerald-200",
  backtest: "bg-amber-50 border-amber-200",
};

const FAMILY_BADGE: Record<string, string> = {
  options_pricing: "bg-sky-100 text-sky-800 border-sky-300",
  risk_metrics: "bg-rose-100 text-rose-800 border-rose-300",
  portfolio_optimization: "bg-emerald-100 text-emerald-800 border-emerald-300",
  backtest: "bg-amber-100 text-amber-800 border-amber-300",
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
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!open || methods !== null) return;
    listMethods()
      .then(setMethods)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [open, methods]);

  // Group by family, sorted in canonical order so swim lanes are stable.
  const grouped: Record<string, MethodEntry[]> = {};
  if (methods) {
    for (const m of methods) (grouped[m.family] ??= []).push(m);
  }
  const families = FAMILY_ORDER.filter((f) => grouped[f]?.length);

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
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[88vh] w-[95vw] max-w-6xl -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl bg-white p-6 shadow-xl">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-base font-semibold text-zinc-900">
                Verified methods
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-xs text-zinc-600">
                Every family runs N independent calculators that cross-verify
                each other. Each method publishes its inputs, the invariants it
                checks, and which siblings act as its cross-verifier.
              </Dialog.Description>
            </div>
            <Dialog.Close
              className="rounded-md p-1 text-zinc-500 transition hover:bg-zinc-100"
              aria-label="Close"
            >
              ×
            </Dialog.Close>
          </div>

          {/* Legend */}
          <div className="mb-3 flex flex-wrap gap-3 text-[11px] text-zinc-600">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
              invariant checked
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-zinc-400" />
              input required
            </span>
            <span className="flex items-center gap-1.5">
              <span className="rounded border border-zinc-300 bg-white px-1.5 font-mono text-[10px]">
                ↔
              </span>
              cross-verified by
            </span>
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
              {families.map((family) => (
                <FamilyLane
                  key={family}
                  family={family}
                  entries={grouped[family]}
                  selectedId={selected}
                  onSelect={setSelected}
                />
              ))}
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function FamilyLane({
  family,
  entries,
  selectedId,
  onSelect,
}: {
  family: string;
  entries: MethodEntry[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  return (
    <section
      className={`mb-5 rounded-2xl border p-4 ${FAMILY_ACCENT[family] ?? "bg-zinc-50 border-zinc-200"}`}
    >
      <div className="mb-3 flex items-center gap-3">
        <span
          className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${
            FAMILY_BADGE[family] ?? "bg-zinc-100 text-zinc-800 border-zinc-300"
          }`}
        >
          {FAMILY_LABELS[family] ?? family}
        </span>
        <span className="text-[11px] text-zinc-500">
          {entries.length} independent method{entries.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {entries.map((m) => (
          <MethodNode
            key={m.calculator_id}
            method={m}
            expanded={selectedId === m.calculator_id}
            onToggle={() =>
              onSelect(selectedId === m.calculator_id ? null : m.calculator_id)
            }
          />
        ))}
      </div>
    </section>
  );
}

function MethodNode({
  method,
  expanded,
  onToggle,
}: {
  method: MethodEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className={`rounded-xl border bg-white p-3 shadow-sm transition ${
        expanded ? "border-zinc-900 ring-1 ring-zinc-900" : "border-zinc-200"
      }`}
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full text-left"
        aria-expanded={expanded}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-zinc-900">
              {method.method_name}
            </div>
            <div className="mt-0.5 truncate font-mono text-[10px] text-zinc-500">
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
        <p className="mt-2 text-xs leading-relaxed text-zinc-700">
          {method.one_line}
        </p>
      </button>

      {/* Invariant chips — always visible (the headline differentiator) */}
      <div className="mt-3 space-y-1.5">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
          Invariants
        </div>
        <div className="flex flex-wrap gap-1">
          {method.invariants_checked.map((inv) => (
            <Chip key={inv} color="emerald" text={inv} />
          ))}
        </div>
      </div>

      {/* Cross-verified-by chips — these are the "arrows" between methods */}
      {method.independent_methods.length > 0 && (
        <div className="mt-2.5 space-y-1.5">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
            ↔ Cross-verified by
          </div>
          <div className="flex flex-wrap gap-1">
            {method.independent_methods.map((id) => (
              <span
                key={id}
                className="rounded border border-zinc-300 bg-zinc-50 px-1.5 py-0.5 font-mono text-[10px] text-zinc-700"
              >
                {id}
              </span>
            ))}
          </div>
        </div>
      )}

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-zinc-200 pt-3 text-xs text-zinc-700">
          <p className="leading-relaxed">{method.long_description}</p>

          <Bullets title="Inputs required" items={method.inputs_required} />
          <Bullets title="Works well when" items={method.domain_of_validity} />
          <Bullets
            title="Breaks or is biased when"
            items={method.domain_limits}
            color="rose"
          />
        </div>
      )}
    </div>
  );
}

function Chip({
  color,
  text,
}: {
  color: "emerald" | "rose" | "zinc";
  text: string;
}) {
  const classes = {
    emerald: "bg-emerald-50 text-emerald-800 border-emerald-200",
    rose: "bg-rose-50 text-rose-800 border-rose-200",
    zinc: "bg-zinc-50 text-zinc-700 border-zinc-200",
  }[color];
  return (
    <span
      className={`rounded border px-1.5 py-0.5 text-[10px] leading-snug ${classes}`}
    >
      {text}
    </span>
  );
}

function Bullets({
  title,
  items,
  color,
}: {
  title: string;
  items: string[];
  color?: "rose";
}) {
  if (items.length === 0) return null;
  const dot = color === "rose" ? "bg-rose-400" : "bg-zinc-400";
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </div>
      <ul className="mt-1 space-y-0.5">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span
              className={`mt-1.5 inline-block h-1 w-1 rounded-full ${dot}`}
            />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
