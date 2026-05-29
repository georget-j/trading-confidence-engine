/**
 * Methods Lab API client.
 *
 * Talks to the backend `/lab/methods` and `/lab/run` endpoints. The Lab UI
 * uses these to let an advanced user invoke a single calculator with raw
 * inputs and see the unaltered `CalculatorResult` (no cross-method check,
 * no invariants, no sensitivity — just one method's number).
 */

import type { CalculatorResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type LabFamily = "options" | "var" | "portfolio" | "backtest";
export type LabCost = "negligible" | "cheap" | "moderate" | "expensive";

export interface MethodDescriptor {
  method_id: string;
  method_name: string;
  family: LabFamily;
  one_line: string;
  independent_from: string[];
  cost: LabCost;
}

export interface LabRunRequest {
  method_id: string;
  // Inputs shape varies by family; Pydantic validates server-side and
  // returns a 422 with a descriptive detail if anything is missing.
  inputs: Record<string, unknown>;
  // Optional escape hatches that let the caller supply returns directly
  // instead of hitting the data provider — useful for offline runs.
  returns?: number[];
  returns_matrix?: number[][];
}

export interface LabRunResponse {
  method_id: string;
  method_name: string;
  family: LabFamily;
  result: CalculatorResult;
}

export async function listLabMethods(): Promise<MethodDescriptor[]> {
  const r = await fetch(`${API_BASE}/lab/methods`);
  if (!r.ok) throw new Error(`Lab API ${r.status}: ${await r.text()}`);
  return (await r.json()) as MethodDescriptor[];
}

export async function runLabMethod(
  req: LabRunRequest,
): Promise<LabRunResponse> {
  const r = await fetch(`${API_BASE}/lab/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    // The lab returns 422 for input validation errors with a structured
    // `detail` — show that to the user verbatim so they know what to fix.
    const text = await r.text();
    throw new Error(`Lab API ${r.status}: ${text}`);
  }
  return (await r.json()) as LabRunResponse;
}
