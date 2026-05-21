import type { FinalAnswer, OptionsPricingRequest } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function priceOption(
  payload: OptionsPricingRequest,
): Promise<FinalAnswer> {
  const r = await fetch(`${API_BASE}/calc/options/price`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`API ${r.status}: ${text}`);
  }
  return (await r.json()) as FinalAnswer;
}
