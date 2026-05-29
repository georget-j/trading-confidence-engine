/**
 * Peer comparison client (Phase 7e).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface PeerCandidate {
  ticker: string;
  name: string;
  sector: string;
  kind: "etf" | "stock";
  correlation: number;
  spot: number | null;
  market_cap: number | null;
  same_industry: boolean;
  is_cheaper: boolean;
}

export interface PeerComparisonResponse {
  reference_ticker: string;
  reference_name: string | null;
  reference_sector: string | null;
  reference_industry: string | null;
  reference_spot: number | null;
  reference_market_cap: number | null;
  peers: PeerCandidate[];
  universe_size: number;
  lookback_days: number;
  limitations: string[];
}

export async function fetchPeers(opts: {
  ticker: string;
  lookbackDays?: number;
  topK?: number;
  minCorrelation?: number;
  cheaperOnly?: boolean;
}): Promise<PeerComparisonResponse> {
  const params = new URLSearchParams();
  if (opts.lookbackDays !== undefined)
    params.set("lookback_days", String(opts.lookbackDays));
  if (opts.topK !== undefined) params.set("top_k", String(opts.topK));
  if (opts.minCorrelation !== undefined)
    params.set("min_correlation", String(opts.minCorrelation));
  if (opts.cheaperOnly) params.set("cheaper_than", "true");
  const qs = params.toString();
  const path = `/api/compare/${encodeURIComponent(opts.ticker.toUpperCase())}/peers${qs ? `?${qs}` : ""}`;
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) throw new Error(`Compare API ${r.status}: ${await r.text()}`);
  return (await r.json()) as PeerComparisonResponse;
}
