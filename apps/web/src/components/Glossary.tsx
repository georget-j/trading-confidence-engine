"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import { GLOSSARY, type GlossaryEntry } from "@/lib/copy";

interface Props {
  /** Optional open-state binding for parent control (e.g. opened from a tour). */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Trigger element. Defaults to a plain text button suitable for the header. */
  trigger?: React.ReactNode;
}

export function Glossary({ open, onOpenChange, trigger }: Props) {
  const [query, setQuery] = useState("");
  const lower = query.toLowerCase();
  const filtered: GlossaryEntry[] = lower
    ? GLOSSARY.filter(
        (e) =>
          e.term.toLowerCase().includes(lower) ||
          e.short.toLowerCase().includes(lower) ||
          e.long.toLowerCase().includes(lower),
      )
    : GLOSSARY;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Trigger asChild>
        {trigger ?? (
          <button
            type="button"
            className="text-xs font-medium text-zinc-600 transition hover:text-zinc-900"
          >
            Glossary
          </button>
        )}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[92vw] max-w-2xl -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl bg-white p-4 shadow-xl sm:p-6">
          <div className="mb-3 flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-base font-semibold text-zinc-900">
                Glossary
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-xs text-zinc-600">
                Plain-English definitions for the terms used in this engine.
              </Dialog.Description>
            </div>
            <Dialog.Close
              className="-mr-2 -mt-2 inline-flex h-11 w-11 items-center justify-center rounded-md text-2xl leading-none text-zinc-500 transition hover:bg-zinc-100"
              aria-label="Close glossary"
            >
              ×
            </Dialog.Close>
          </div>

          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the glossary…"
            className="mb-3 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
          />

          <div className="flex-1 overflow-y-auto pr-1">
            {filtered.length === 0 ? (
              <div className="py-8 text-center text-sm text-zinc-500">
                No matches.
              </div>
            ) : (
              <ul className="space-y-3">
                {filtered.map((entry) => (
                  <li
                    key={entry.term}
                    className="rounded-lg border border-zinc-200 p-3"
                  >
                    <div className="text-sm font-semibold text-zinc-900">
                      {entry.term}
                    </div>
                    <div className="mt-0.5 text-xs italic text-zinc-600">
                      {entry.short}
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-zinc-700">
                      {entry.long}
                    </p>
                    {entry.alsoSee && entry.alsoSee.length > 0 && (
                      <div className="mt-2 text-[10px] text-zinc-500">
                        See also:{" "}
                        {entry.alsoSee.map((s, i) => (
                          <span key={s}>
                            {i > 0 && ", "}
                            <span className="text-zinc-700">{s}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
