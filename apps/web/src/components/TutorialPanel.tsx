"use client";

import { useState, type ReactNode } from "react";
import { useTutorial, type TutorialTab } from "@/lib/tutorial";
import { CalloutLegend, type CalloutItem } from "./TutorialCallout";

export interface TutorialTerm {
  term: string;
  definition: ReactNode;
}

export interface TutorialTabConfig {
  tab: TutorialTab;
  /** Human-readable name of the tab, used in headings/buttons. */
  tabName: string;
  /** 1–2 sentence plain-English description of what this tab does. */
  whatItDoes: ReactNode;
  /** Plain-English definitions of every term that appears on this tab. */
  terms: TutorialTerm[];
  /** Heading for the worked example (e.g. "Worked example: price an SPY call"). */
  exampleTitle: string;
  /** Plain-English narrative for the worked example before the user runs it. */
  examplePreamble: ReactNode;
  /** Label for the action button (e.g. "Walk me through it"). */
  exampleCta: string;
  /** Called when the user clicks the example CTA. Should populate
   *  the tab's state with the worked-example inputs + result. */
  onRunExample: () => void;
  /** Optional: render annotated callouts to read alongside the result. */
  exampleCallouts?: CalloutItem[];
  /** Whether the example has been run yet (so callouts can be conditional). */
  exampleHasRun?: boolean;
}

interface Props {
  config: TutorialTabConfig;
}

export function TutorialPanel({ config }: Props) {
  const { isExpanded, dismiss } = useTutorial();
  const [termsOpen, setTermsOpen] = useState(false);

  if (!isExpanded(config.tab)) {
    return null;
  }

  return (
    <section className="mb-6 rounded-2xl border border-indigo-200 bg-indigo-50/40 p-4 shadow-sm sm:p-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-indigo-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
              Learn
            </span>
            <h2 className="text-sm font-semibold text-zinc-900">
              {config.tabName}
            </h2>
          </div>
          <p className="mt-2 max-w-3xl text-xs leading-relaxed text-zinc-700 sm:text-sm">
            {config.whatItDoes}
          </p>
        </div>
        <button
          type="button"
          onClick={() => dismiss(config.tab)}
          className="self-start rounded-md border border-zinc-300 bg-white px-2.5 py-1.5 text-[11px] font-medium text-zinc-600 transition hover:bg-zinc-100 sm:shrink-0 sm:py-1"
          aria-label="Hide tutorial for this tab"
        >
          Got it — hide
        </button>
      </header>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_1fr]">
        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <button
            type="button"
            onClick={() => setTermsOpen((o) => !o)}
            className="flex w-full items-center justify-between text-left text-xs font-semibold uppercase tracking-wide text-zinc-500"
            aria-expanded={termsOpen}
          >
            <span>Terms you&apos;ll see ({config.terms.length})</span>
            <span aria-hidden className="text-zinc-400">
              {termsOpen ? "▾" : "▸"}
            </span>
          </button>
          {termsOpen ? (
            <dl className="mt-3 space-y-2.5">
              {config.terms.map((t) => (
                <div key={t.term}>
                  <dt className="text-xs font-semibold text-zinc-900">
                    {t.term}
                  </dt>
                  <dd className="mt-0.5 text-xs leading-relaxed text-zinc-700">
                    {t.definition}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="mt-2 text-xs text-zinc-600">
              {config.terms
                .slice(0, 8)
                .map((t) => t.term)
                .join(" · ")}
              {config.terms.length > 8 ? " · …" : ""}
            </p>
          )}
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
            {config.exampleTitle}
          </div>
          <p className="mt-2 text-xs leading-relaxed text-zinc-700">
            {config.examplePreamble}
          </p>
          <button
            type="button"
            onClick={config.onRunExample}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-700"
          >
            <span aria-hidden>▶</span>
            {config.exampleCta}
          </button>
          {config.exampleHasRun && config.exampleCallouts ? (
            <div className="mt-4 border-t border-zinc-200 pt-3">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
                Read these callouts on the result
              </div>
              <CalloutLegend items={config.exampleCallouts} />
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

/** Header toggle: lets the user re-show or hide tutorials globally. */
export function TutorialToggle() {
  const { globalOverride, setGlobalOverride } = useTutorial();

  // Tri-state cycle: null → show → hide → null (back to per-tab defaults)
  function handleClick() {
    if (globalOverride === null) setGlobalOverride("show");
    else if (globalOverride === "show") setGlobalOverride("hide");
    else setGlobalOverride(null);
  }

  const label =
    globalOverride === "show"
      ? "Tutorials: on"
      : globalOverride === "hide"
        ? "Tutorials: off"
        : "Tutorials";

  const title =
    globalOverride === "show"
      ? "Tutorials forced on for every tab. Click to hide them everywhere."
      : globalOverride === "hide"
        ? "Tutorials hidden everywhere. Click to revert to per-tab defaults."
        : "Per-tab defaults (each tab shows its tutorial until you dismiss it). Click to force tutorials on.";

  return (
    <button
      type="button"
      onClick={handleClick}
      title={title}
      className={`font-medium transition ${
        globalOverride === "show"
          ? "text-indigo-700 hover:text-indigo-900"
          : globalOverride === "hide"
            ? "text-zinc-400 hover:text-zinc-600"
            : "text-zinc-600 hover:text-zinc-900"
      }`}
    >
      {label}
    </button>
  );
}
