/**
 * Ticker info + options-chain client (Phase 7 Trade Ideas tab).
 *
 * Wraps `/api/ticker/{ticker}/summary`, `/expiries`, and `/chain` with
 * lightweight typed accessors. All errors surface as thrown `Error` so the
 * caller can show a friendly message; no silent fallback values.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface TickerSummary {
  ticker: string;
  spot: number;
  spot_currency: string;
  realised_vol_annualised: number;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  short_name: string | null;
  long_name: string | null;
}

export interface OptionChainEntry {
  contract_symbol: string;
  option_type: "call" | "put";
  strike: number;
  last_price: number | null;
  bid: number | null;
  ask: number | null;
  volume: number | null;
  open_interest: number | null;
  implied_volatility: number | null;
  in_the_money: boolean;
}

export interface OptionsChain {
  ticker: string;
  expiry: string;
  spot: number;
  entries: OptionChainEntry[];
}

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`Ticker API ${r.status}: ${text}`);
  }
  return (await r.json()) as T;
}

export function fetchTickerSummary(ticker: string): Promise<TickerSummary> {
  const t = encodeURIComponent(ticker.trim().toUpperCase());
  return getJson<TickerSummary>(`/api/ticker/${t}/summary`);
}

export function fetchExpiries(
  ticker: string,
): Promise<{ ticker: string; expiries: string[] }> {
  const t = encodeURIComponent(ticker.trim().toUpperCase());
  return getJson<{ ticker: string; expiries: string[] }>(
    `/api/ticker/${t}/expiries`,
  );
}

export function fetchOptionsChain(
  ticker: string,
  expiry: string,
): Promise<OptionsChain> {
  const t = encodeURIComponent(ticker.trim().toUpperCase());
  const e = encodeURIComponent(expiry);
  return getJson<OptionsChain>(`/api/ticker/${t}/chain?expiry=${e}`);
}
