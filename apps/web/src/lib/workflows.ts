"use client";

/**
 * Saved-workflow storage layer.
 *
 * V8-lightweight: localStorage-backed, single-device. Stores the request
 * payload for any of the four families plus a label and timestamp. The
 * stored payload is enough to re-run end-to-end on the existing endpoints
 * — no server-side state, no auth.
 *
 * The full V8 from the original plan (scheduled jobs, confidence-trend
 * tracking, notifications) needs Postgres + auth and lands in a later
 * milestone.
 */

import type {
  BacktestRequest,
  OptionsPricingRequest,
  PortfolioRequest,
  VaRRequest,
} from "./types";

const STORAGE_KEY = "tce.saved_workflows_v1";

export type SavedFamily = "options" | "risk" | "portfolio" | "backtest";

export interface SavedWorkflow {
  id: string;
  family: SavedFamily;
  label: string;
  created_at: string;
  payload:
    | OptionsPricingRequest
    | VaRRequest
    | PortfolioRequest
    | BacktestRequest;
  /** Optional summary line cached at save-time (verification status + headline number). */
  summary?: string;
}

function read(): SavedWorkflow[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedWorkflow[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(workflows: SavedWorkflow[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(workflows));
}

export function listWorkflows(): SavedWorkflow[] {
  return read().sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export function saveWorkflow(
  family: SavedFamily,
  label: string,
  payload: SavedWorkflow["payload"],
  summary?: string,
): SavedWorkflow {
  const wf: SavedWorkflow = {
    id: `${family}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    family,
    label: label.trim() || `${family} ${new Date().toLocaleString()}`,
    created_at: new Date().toISOString(),
    payload,
    summary,
  };
  write([wf, ...read()]);
  return wf;
}

export function deleteWorkflow(id: string): void {
  write(read().filter((w) => w.id !== id));
}

/** Subscribe to changes — used by the Saved panel to live-update.
 *  Returns an unsubscribe function. */
export function subscribeWorkflows(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const handler = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) listener();
  };
  window.addEventListener("storage", handler);
  // Same-tab updates: a small event-bus on window so saveWorkflow can fire it.
  const onLocal = () => listener();
  window.addEventListener("tce-workflows-changed", onLocal as EventListener);
  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener(
      "tce-workflows-changed",
      onLocal as EventListener,
    );
  };
}

/** Dispatch a same-tab refresh event after save/delete. */
export function notifyWorkflowsChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("tce-workflows-changed"));
}
