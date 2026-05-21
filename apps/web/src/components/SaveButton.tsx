"use client";

import { useState } from "react";
import {
  notifyWorkflowsChanged,
  saveWorkflow,
  type SavedFamily,
} from "@/lib/workflows";

interface Props {
  family: SavedFamily;
  payload: object;
  defaultLabel: string;
  summary?: string;
}

/** Inline "save" control. Click → small input appears → Enter to save.
 *  Keeps the saved-workflow surface area minimal in each result card. */
export function SaveButton({ family, payload, defaultLabel, summary }: Props) {
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(defaultLabel);
  const [saved, setSaved] = useState(false);

  function persist() {
    saveWorkflow(family, label, payload as never, summary);
    notifyWorkflowsChanged();
    setEditing(false);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2000);
  }

  if (saved) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-[10px] font-medium text-emerald-800">
        ✓ Saved
      </span>
    );
  }

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => {
          setLabel(defaultLabel);
          setEditing(true);
        }}
        className="rounded-md border border-zinc-300 px-2.5 py-1 text-[11px] font-medium text-zinc-700 transition hover:bg-zinc-50"
      >
        Save workflow
      </button>
    );
  }

  return (
    <div className="inline-flex items-center gap-1">
      <input
        autoFocus
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") persist();
          if (e.key === "Escape") setEditing(false);
        }}
        className="w-48 rounded-md border border-zinc-300 px-2 py-1 text-[11px] outline-none focus:border-zinc-500"
        placeholder="Label this workflow"
      />
      <button
        type="button"
        onClick={persist}
        className="rounded-md bg-zinc-900 px-2 py-1 text-[11px] font-semibold text-white transition hover:bg-zinc-800"
      >
        Save
      </button>
      <button
        type="button"
        onClick={() => setEditing(false)}
        className="rounded-md border border-zinc-300 px-2 py-1 text-[11px] text-zinc-700 transition hover:bg-zinc-50"
      >
        Cancel
      </button>
    </div>
  );
}
