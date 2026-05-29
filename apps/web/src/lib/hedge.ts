/**
 * Hedge finder client (Phase 7d).
 */

import type { Holding } from "./portfolio_import";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface HedgeCandidate {
  ticker: string;
  name: string;
  kind: "etf" | "stock";
  universe_sector: string;
  correlation: number;
  recent_correlation: number;
  half_life_warning: boolean;
}

export interface SectorHedgeSuggestion {
  sector: string;
  sector_weight: number;
  candidates: HedgeCandidate[];
}

export interface HedgeSuggestResponse {
  suggestions: SectorHedgeSuggestion[];
  universe_size: number;
  lookback_days: number;
  disclaimer: string;
  limitations: string[];
}

export interface HedgeSuggestRequest {
  holdings: Holding[];
  lookback_days?: number;
  top_k?: number;
  min_sector_weight?: number;
}

export async function suggestHedges(
  req: HedgeSuggestRequest,
): Promise<HedgeSuggestResponse> {
  const r = await fetch(`${API_BASE}/api/hedge/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`Hedge API ${r.status}: ${text}`);
  }
  return (await r.json()) as HedgeSuggestResponse;
}
