"use client";

/**
 * Home tab — three big cards. The deliberate "what do you want to do?"
 * landing surface that replaces the old default of dumping the user
 * straight into Trade Ideas.
 *
 * Each card has:
 *   - One short verb-phrase title
 *   - One plain-English description (no jargon)
 *   - One tiny visual hint
 *   - A call-to-action button that jumps to the right tab
 *
 * No technical jargon, no verification metadata, no disclaimer noise.
 * Just three doors. Click one, you're in.
 */

import type { ReactNode } from "react";

export type HomeDestination =
  | "trade_ideas"
  | "my_portfolio"
  | "hedge_finder"
  | "compare";

interface Props {
  onPick: (destination: HomeDestination) => void;
}

export function Home({ onPick }: Props) {
  return (
    <div className="space-y-6">
      <header className="text-center sm:py-4">
        <h2 className="text-lg font-semibold text-zinc-900 sm:text-xl">
          What do you want to do?
        </h2>
        <p className="mx-auto mt-1 max-w-xl text-xs text-zinc-600 sm:text-sm">
          Pick a starting point. You can always switch later from the tabs at
          the top.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card
          icon="🔍"
          title="Look up a stock"
          body="Pull a real ticker (TSLA, AAPL, SPY…) and see what an option position would be worth — plus what happens if the market moves."
          ctaLabel="Look up a stock"
          onClick={() => onPick("trade_ideas")}
          tint="indigo"
        />
        <Card
          icon="📊"
          title="Analyse my portfolio"
          body="Paste your holdings or upload a Trading 212 CSV. See your sector mix, biggest positions, and how your stocks move together."
          ctaLabel="Analyse holdings"
          onClick={() => onPick("my_portfolio")}
          tint="emerald"
        />
        <Card
          icon="🛡️"
          title="Find a hedge"
          body="Got too much exposure to one sector? We'll scan a universe of stocks and ETFs for things that historically move the opposite way."
          ctaLabel="Find a hedge"
          onClick={() => onPick("hedge_finder")}
          tint="amber"
        />
        <Card
          icon="↔️"
          title="Find similar stocks"
          body="Pick a ticker (like NVDA) and we'll rank stocks that move similarly — useful for finding cheaper alternatives in the same theme."
          ctaLabel="Compare peers"
          onClick={() => onPick("compare")}
          tint="rose"
          spanFull
        />
      </div>

      <section className="rounded-2xl border border-zinc-200 bg-white p-4 text-xs text-zinc-600 sm:p-6 sm:text-sm">
        <h3 className="text-sm font-semibold text-zinc-900">
          Why trust the numbers here?
        </h3>
        <p className="mt-2 leading-relaxed">
          Every number is computed by at least two independent methods that have
          to agree before we call the result <em>verified</em>. If they
          disagree, you&apos;ll see <em>partially verified</em> — usually a real
          signal (like fat-tailed returns) rather than a bug. Click any number
          to see exactly how it was checked.
        </p>
      </section>
    </div>
  );
}

function Card({
  icon,
  title,
  body,
  ctaLabel,
  onClick,
  tint,
  spanFull,
}: {
  icon: string;
  title: string;
  body: ReactNode;
  ctaLabel: string;
  onClick: () => void;
  tint: "indigo" | "emerald" | "amber" | "rose";
  spanFull?: boolean;
}) {
  const tintMap: Record<string, string> = {
    indigo: "border-indigo-200 bg-indigo-50/40",
    emerald: "border-emerald-200 bg-emerald-50/40",
    amber: "border-amber-200 bg-amber-50/40",
    rose: "border-rose-200 bg-rose-50/40",
  };
  const buttonTint: Record<string, string> = {
    indigo: "bg-indigo-600 hover:bg-indigo-700",
    emerald: "bg-emerald-600 hover:bg-emerald-700",
    amber: "bg-amber-600 hover:bg-amber-700",
    rose: "bg-rose-600 hover:bg-rose-700",
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group flex flex-col rounded-2xl border p-5 text-left shadow-sm transition hover:shadow-md sm:p-6 ${tintMap[tint]} ${spanFull ? "sm:col-span-2 lg:col-span-3" : ""}`}
    >
      <div className="text-3xl" aria-hidden>
        {icon}
      </div>
      <h3 className="mt-3 text-base font-semibold text-zinc-900">{title}</h3>
      <p className="mt-2 flex-1 text-sm leading-relaxed text-zinc-700">
        {body}
      </p>
      <span
        className={`mt-4 inline-flex w-fit items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition ${buttonTint[tint]}`}
      >
        {ctaLabel} →
      </span>
    </button>
  );
}
