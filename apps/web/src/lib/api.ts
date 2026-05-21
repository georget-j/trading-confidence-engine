import type {
  ChatParseResponse,
  FinalAnswer,
  OptionsPricingRequest,
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
