"use client";

import { useState } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import {
  DEFAULT_FORM_STATE,
  formStateFromRequest,
  PricingForm,
  type PricingFormState,
} from "@/components/PricingForm";
import { ResultCard } from "@/components/ResultCard";
import { RiskForm } from "@/components/RiskForm";
import { RiskResultCard } from "@/components/RiskResultCard";
import { computeVaR, priceOption } from "@/lib/api";
import type {
  FinalAnswer,
  OptionsPricingRequest,
  VaRRequest,
} from "@/lib/types";

type Tab = "options" | "risk";

export default function Home() {
  const [tab, setTab] = useState<Tab>("options");

  // Per-tab state — kept separate so switching tabs doesn't wipe the other side.
  const [optionsState, setOptionsState] =
    useState<PricingFormState>(DEFAULT_FORM_STATE);
  const [optionsAnswer, setOptionsAnswer] = useState<FinalAnswer | null>(null);
  const [optionsRequest, setOptionsRequest] =
    useState<OptionsPricingRequest | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [highlightForm, setHighlightForm] = useState(false);

  const [riskAnswer, setRiskAnswer] = useState<FinalAnswer | null>(null);
  const [riskRequest, setRiskRequest] = useState<VaRRequest | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState<string | null>(null);

  async function handlePriceOption(req: OptionsPricingRequest) {
    setOptionsError(null);
    setOptionsLoading(true);
    try {
      const result = await priceOption(req);
      setOptionsAnswer(result);
      setOptionsRequest(req);
    } catch (e) {
      setOptionsError(e instanceof Error ? e.message : String(e));
      setOptionsAnswer(null);
      setOptionsRequest(null);
    } finally {
      setOptionsLoading(false);
    }
  }

  function handleChatParsed(req: OptionsPricingRequest) {
    setOptionsState(formStateFromRequest(req));
    setHighlightForm(true);
    window.setTimeout(() => setHighlightForm(false), 1500);
  }

  async function handleComputeVaR(req: VaRRequest) {
    setRiskError(null);
    setRiskLoading(true);
    try {
      const result = await computeVaR(req);
      setRiskAnswer(result);
      setRiskRequest(req);
    } catch (e) {
      setRiskError(e instanceof Error ? e.message : String(e));
      setRiskAnswer(null);
      setRiskRequest(null);
    } finally {
      setRiskLoading(false);
    }
  }

  return (
    <main className="min-h-dvh bg-zinc-50">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <header className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
            Trading Confidence Engine
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-zinc-600">
            Independent calculators cross-verified against domain invariants.
            Every answer carries a verification status — the engine refuses to
            confidently report what it can&apos;t verify.
          </p>
        </header>

        <div className="mb-6 inline-flex rounded-lg border border-zinc-300 bg-white p-0.5 shadow-sm">
          <TabButton
            active={tab === "options"}
            onClick={() => setTab("options")}
          >
            Options pricing
          </TabButton>
          <TabButton active={tab === "risk"} onClick={() => setTab("risk")}>
            Value at Risk
          </TabButton>
        </div>

        {tab === "options" && (
          <div className="grid gap-6 lg:grid-cols-[1fr_1fr_1.2fr]">
            <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                Chat input
              </h2>
              <ChatPanel onParsed={handleChatParsed} />
            </section>

            <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                European option
              </h2>
              <PricingForm
                state={optionsState}
                onChange={setOptionsState}
                onSubmit={handlePriceOption}
                loading={optionsLoading}
                highlight={highlightForm}
              />
            </section>

            <ResultSection
              loading={optionsLoading}
              error={optionsError}
              empty="Enter inputs and price an option."
              emptyDetail="py_vollib closed-form and QuantLib Leisen-Reimer binomial run, then a cross-method verifier and no-arbitrage invariants decide the status."
            >
              {optionsAnswer && (
                <ResultCard
                  answer={optionsAnswer}
                  request={optionsRequest ?? undefined}
                />
              )}
            </ResultSection>
          </div>
        )}

        {tab === "risk" && (
          <div className="grid gap-6 lg:grid-cols-[1fr_1.5fr]">
            <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                VaR / CVaR
              </h2>
              <RiskForm onSubmit={handleComputeVaR} loading={riskLoading} />
            </section>

            <ResultSection
              loading={riskLoading}
              error={riskError}
              empty="Pick a ticker and compute VaR."
              emptyDetail="Three independent methods (historical, parametric, Monte Carlo) cross-verified. Divergence between methods becomes a signal about fat tails in the data."
            >
              {riskAnswer && (
                <RiskResultCard
                  answer={riskAnswer}
                  request={riskRequest ?? undefined}
                />
              )}
            </ResultSection>
          </div>
        )}

        <footer className="mt-12 text-xs text-zinc-500">
          Not investment advice. Calculation engine for educational/analytical
          use.
        </footer>
      </div>
    </main>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
        active ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-100"
      }`}
    >
      {children}
    </button>
  );
}

function ResultSection({
  loading,
  error,
  empty,
  emptyDetail,
  children,
}: {
  loading: boolean;
  error: string | null;
  empty: string;
  emptyDetail: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <div className="font-semibold">Request failed</div>
          <div className="mt-1 font-mono text-xs">{error}</div>
        </div>
      )}
      {!children && !error && !loading && (
        <div className="flex h-full min-h-[420px] flex-col items-center justify-center text-center text-sm text-zinc-500">
          <div className="mb-2 text-4xl">🔍</div>
          <div className="font-medium text-zinc-700">{empty}</div>
          <div className="mt-1 max-w-xs text-xs text-zinc-500">
            {emptyDetail}
          </div>
        </div>
      )}
      {children}
    </section>
  );
}
