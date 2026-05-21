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
import { priceOption } from "@/lib/api";
import type { FinalAnswer, OptionsPricingRequest } from "@/lib/types";

export default function Home() {
  const [formState, setFormState] =
    useState<PricingFormState>(DEFAULT_FORM_STATE);
  const [answer, setAnswer] = useState<FinalAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [highlightForm, setHighlightForm] = useState(false);

  async function handlePrice(req: OptionsPricingRequest) {
    setError(null);
    setLoading(true);
    try {
      const result = await priceOption(req);
      setAnswer(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setAnswer(null);
    } finally {
      setLoading(false);
    }
  }

  function handleChatParsed(req: OptionsPricingRequest) {
    setFormState(formStateFromRequest(req));
    setHighlightForm(true);
    window.setTimeout(() => setHighlightForm(false), 1500);
  }

  return (
    <main className="min-h-dvh bg-zinc-50">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <header className="mb-10">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
            Trading Confidence Engine
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-zinc-600">
            Options pricing with{" "}
            <span className="font-medium text-zinc-900">
              two independent methods
            </span>{" "}
            cross-verified against no-arbitrage invariants. Ask in plain English
            (the LLM only extracts inputs — it never produces prices) or fill
            the form directly.
          </p>
        </header>

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
              state={formState}
              onChange={setFormState}
              onSubmit={handlePrice}
              loading={loading}
              highlight={highlightForm}
            />
          </section>

          <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            {error && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
                <div className="font-semibold">Request failed</div>
                <div className="mt-1 font-mono text-xs">{error}</div>
              </div>
            )}
            {!answer && !error && (
              <div className="flex h-full min-h-[420px] flex-col items-center justify-center text-center text-sm text-zinc-500">
                <div className="mb-2 text-4xl">🔍</div>
                <div className="font-medium text-zinc-700">
                  Enter inputs and price an option.
                </div>
                <div className="mt-1 max-w-xs text-xs text-zinc-500">
                  py_vollib closed-form and QuantLib Leisen-Reimer binomial will
                  both run, then a cross-method verifier and no-arbitrage
                  invariants decide the verification status.
                </div>
              </div>
            )}
            {answer && <ResultCard answer={answer} />}
          </section>
        </div>

        <footer className="mt-12 text-xs text-zinc-500">
          Not investment advice. Calculation engine for educational/analytical
          use.
        </footer>
      </div>
    </main>
  );
}
