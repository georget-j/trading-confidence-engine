"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";
import {
  deleteWorkflow,
  listWorkflows,
  notifyWorkflowsChanged,
  subscribeWorkflows,
  type SavedWorkflow,
} from "@/lib/workflows";

interface Props {
  /** Called when the user picks a workflow — parent dispatches it to the
   *  right form/runner based on `family`. */
  onLoad: (workflow: SavedWorkflow) => void;
}

const FAMILY_LABEL: Record<string, string> = {
  options: "Options",
  risk: "Risk (VaR)",
  portfolio: "Portfolio",
  backtest: "Backtest",
};

const FAMILY_CHIP: Record<string, string> = {
  options: "bg-sky-100 text-sky-800",
  risk: "bg-amber-100 text-amber-800",
  portfolio: "bg-emerald-100 text-emerald-800",
  backtest: "bg-violet-100 text-violet-800",
};

export function SavedWorkflows({ onLoad }: Props) {
  const [open, setOpen] = useState(false);
  const [workflows, setWorkflows] = useState<SavedWorkflow[]>([]);

  useEffect(() => {
    if (!open) return;
    setWorkflows(listWorkflows());
    return subscribeWorkflows(() => setWorkflows(listWorkflows()));
  }, [open]);

  function handleDelete(id: string) {
    deleteWorkflow(id);
    notifyWorkflowsChanged();
    setWorkflows(listWorkflows());
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className="text-xs font-medium text-zinc-600 transition hover:text-zinc-900"
        >
          Saved
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[92vw] max-w-2xl -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl bg-white p-6 shadow-xl">
          <div className="mb-3 flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-base font-semibold text-zinc-900">
                Saved workflows
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-xs text-zinc-600">
                Stored locally in your browser. Re-load to re-run with the same
                inputs.
              </Dialog.Description>
            </div>
            <Dialog.Close
              className="rounded-md p-1 text-zinc-500 transition hover:bg-zinc-100"
              aria-label="Close"
            >
              ×
            </Dialog.Close>
          </div>

          {workflows.length === 0 ? (
            <div className="py-10 text-center text-sm text-zinc-500">
              No saved workflows yet. Click{" "}
              <span className="font-mono">Save</span> on any result card to add
              one.
            </div>
          ) : (
            <ul className="flex-1 space-y-2 overflow-y-auto pr-1">
              {workflows.map((w) => (
                <li
                  key={w.id}
                  className="flex items-start gap-3 rounded-lg border border-zinc-200 p-3"
                >
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      FAMILY_CHIP[w.family]
                    }`}
                  >
                    {FAMILY_LABEL[w.family]}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-sm font-medium text-zinc-900">
                      {w.label}
                    </div>
                    {w.summary && (
                      <div className="mt-0.5 text-xs text-zinc-600">
                        {w.summary}
                      </div>
                    )}
                    <div className="mt-0.5 text-[10px] text-zinc-400">
                      Saved {new Date(w.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <button
                      type="button"
                      onClick={() => {
                        onLoad(w);
                        setOpen(false);
                      }}
                      className="rounded-md bg-zinc-900 px-2.5 py-1 text-[11px] font-medium text-white transition hover:bg-zinc-800"
                    >
                      Re-run
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(w.id)}
                      className="rounded-md border border-zinc-300 px-2.5 py-1 text-[11px] font-medium text-zinc-700 transition hover:bg-zinc-50"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
