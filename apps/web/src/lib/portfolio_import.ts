/**
 * Portfolio import + analyse client (Phase 7 My Portfolio tab).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface Holding {
  ticker: string;
  shares: number;
  cost_basis?: number | null;
  currency?: string | null;
}

export interface ImportedPortfolio {
  holdings: Holding[];
  source: string;
  rows_seen: number;
}

export interface PricedHolding {
  ticker: string;
  shares: number;
  cost_basis: number | null;
  currency: string | null;
  spot: number;
  value_usd: number;
  weight: number;
  sector: string | null;
  industry: string | null;
  pnl_usd: number | null;
}

export interface SectorExposure {
  sector: string;
  value_usd: number;
  weight: number;
}

export interface ConcentrationAlert {
  kind: string;
  label: string;
  weight: number;
  threshold: number;
  message: string;
}

export interface CorrelationMatrix {
  tickers: string[];
  matrix: number[][];
}

export interface PortfolioAnalysis {
  total_value_usd: number;
  holdings: PricedHolding[];
  sector_exposure: SectorExposure[];
  concentration_alerts: ConcentrationAlert[];
  portfolio_volatility_annualised: number | null;
  correlation_matrix: CorrelationMatrix | null;
  lookback_days: number;
  limitations: string[];
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`Portfolio API ${r.status}: ${text}`);
  }
  return (await r.json()) as T;
}

export function importPortfolioCsv(
  csvText: string,
  source: "trading_212" | "generic_csv" = "trading_212",
): Promise<ImportedPortfolio> {
  return postJson<ImportedPortfolio>("/api/portfolio/import", {
    csv_text: csvText,
    source,
  });
}

export function importPortfolioHoldings(
  holdings: Holding[],
): Promise<ImportedPortfolio> {
  return postJson<ImportedPortfolio>("/api/portfolio/import", {
    source: "paste",
    holdings,
  });
}

export function analysePortfolio(
  holdings: Holding[],
  lookbackDays: number = 252,
): Promise<PortfolioAnalysis> {
  return postJson<PortfolioAnalysis>("/api/portfolio/analyse", {
    holdings,
    lookback_days: lookbackDays,
  });
}
