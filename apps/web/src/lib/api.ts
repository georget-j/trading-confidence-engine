import type {
  BacktestRequest,
  ChatParseResponse,
  FinalAnswer,
  MethodEntry,
  OptionsPricingRequest,
  PortfolioRequest,
  VaRRequest,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`API ${r.status}: ${text}`);
  }
  return (await r.json()) as T;
}

export function priceOption(
  payload: OptionsPricingRequest,
): Promise<FinalAnswer> {
  return postJson<FinalAnswer>("/calc/options/price", payload);
}

export function parseChat(text: string): Promise<ChatParseResponse> {
  return postJson<ChatParseResponse>("/chat/parse", { text });
}

export function computeVaR(payload: VaRRequest): Promise<FinalAnswer> {
  return postJson<FinalAnswer>("/calc/risk/var", payload);
}

export function optimizePortfolio(
  payload: PortfolioRequest,
): Promise<FinalAnswer> {
  return postJson<FinalAnswer>("/calc/portfolio/optimize", payload);
}

export function runBacktest(payload: BacktestRequest): Promise<FinalAnswer> {
  return postJson<FinalAnswer>("/calc/backtest/run", payload);
}

export async function listMethods(): Promise<MethodEntry[]> {
  const r = await fetch(`${API_BASE}/api/methods`);
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return (await r.json()) as MethodEntry[];
}

export interface PricePoint {
  date: string;
  close: number;
}

export interface PriceHistoryResponse {
  ticker: string;
  points: PricePoint[];
  cached: boolean;
}

export async function fetchPriceHistory(
  ticker: string,
  days: number = 60,
): Promise<PriceHistoryResponse> {
  const r = await fetch(
    `${API_BASE}/api/prices/history?ticker=${encodeURIComponent(ticker)}&days=${days}`,
  );
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return (await r.json()) as PriceHistoryResponse;
}
