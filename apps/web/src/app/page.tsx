"use client";

import { useState } from "react";
import { PricingForm } from "@/components/PricingForm";
import { ResultCard } from "@/components/ResultCard";
import { priceOption } from "@/lib/api";
import type { FinalAnswer, OptionsPricingRequest } from "@/lib/types";

export default function Home() {
  const [answer, setAnswer] = useState<FinalAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(req: OptionsPricingRequest) {
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

  return (
    <main className="min-h-dvh bg-zinc-50">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <header className="mb-10">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
            Trading Confidence Engine
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-zinc-600">
            Options pricing with{" "}
            <span className="font-medium text-zinc-900">
              two independent methods
            </span>{" "}
            cross-verified against no-arbitrage invariants. Every answer carries
            a verification status — the engine refuses to confidently report
            results it can&apos;t verify.
          </p>
        </header>

        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold text-zinc-900">
              European option
            </h2>
            <PricingForm onSubmit={handleSubmit} loading={loading} />
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
