"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";

const STORAGE_KEY = "tce.tour_dismissed_v1";

interface Props {
  /** External control — set true to force-open (e.g. clicking 'Help' link).
   *  Internal first-run logic still applies independently. */
  forceOpen?: boolean;
  onClose?: () => void;
}

interface Step {
  title: string;
  body: React.ReactNode;
  emoji: string;
}

const STEPS: Step[] = [
  {
    title: "How the chat input works",
    emoji: "💬",
    body: (
      <>
        <p>
          On the Options tab there&apos;s a chat box on the left. Type a
          natural-language request like{" "}
          <span className="font-mono text-zinc-900">
            &ldquo;SPY 450 call expiring in 30 days at 18% IV&rdquo;
          </span>{" "}
          and an LLM extracts the structured inputs into the form on the right.
        </p>
        <p className="mt-2 font-semibold text-zinc-900">
          The LLM never produces prices, Greeks, or any number.
        </p>
        <p className="mt-1">
          Final numbers always come from the deterministic calculators — the LLM
          is just a parser. If it can&apos;t confidently extract a field (e.g.
          you didn&apos;t state the spot), it leaves the form alone and tells
          you what&apos;s missing.
        </p>
      </>
    ),
  },
  {
    title: "What &ldquo;verified&rdquo; means",
    emoji: "✅",
    body: (
      <>
        <p>
          Every result is computed by{" "}
          <span className="font-semibold">
            at least two independent calculators
          </span>{" "}
          (different math, different codebases). The engine then cross-checks
          them against each other AND against mathematical invariants like
          put-call parity and no-arbitrage bounds.
        </p>
        <p className="mt-2">
          You&apos;ll see a coloured badge on every result:
        </p>
        <ul className="mt-1 space-y-1 text-xs">
          <li>
            <span className="inline-block rounded bg-emerald-100 px-1.5 font-semibold text-emerald-900">
              Verified
            </span>{" "}
            — methods agreed AND every invariant passed.
          </li>
          <li>
            <span className="inline-block rounded bg-amber-100 px-1.5 font-semibold text-amber-900">
              Partially verified
            </span>{" "}
            — methods diverged enough to be flagged. Often a real signal about
            the data, not a bug.
          </li>
          <li>
            <span className="inline-block rounded bg-rose-100 px-1.5 font-semibold text-rose-900">
              Not verified
            </span>{" "}
            — methods disagreed badly or an invariant failed. Don&apos;t act on
            this number.
          </li>
        </ul>
        <p className="mt-2 text-zinc-600">
          Click the badge in any result to see a worked example.
        </p>
      </>
    ),
  },
  {
    title: "Real data often goes partial — that&apos;s the point",
    emoji: "📊",
    body: (
      <>
        <p>
          On the <span className="font-semibold">Value at Risk</span> tab, try
          ticker <span className="font-mono text-zinc-900">SPY</span>. The
          result will probably come back{" "}
          <span className="inline-block rounded bg-amber-100 px-1.5 font-semibold text-amber-900">
            partially verified
          </span>{" "}
          — and that is a feature, not a bug.
        </p>
        <p className="mt-2">
          SPY (and most real equities) have{" "}
          <span className="font-semibold">fat tails</span>: extreme down-days
          happen more often than a normal distribution predicts. The parametric
          (normal-assumption) VaR underestimates the risk; the historical
          (no-assumption) VaR captures it. The methods diverge, the engine flags
          it, and the histogram chart shows you what&apos;s happening.
        </p>
        <p className="mt-2 text-zinc-600">
          Use the historical number as your safest single estimate when you see
          partial verification.
        </p>
      </>
    ),
  },
  {
    title: "New here? Try the per-tab tutorials",
    emoji: "🎓",
    body: (
      <>
        <p>
          Every tab has a{" "}
          <span className="inline-block rounded bg-indigo-100 px-1.5 font-semibold text-indigo-900">
            Learn this tab
          </span>{" "}
          panel at the top. It explains every term you&apos;ll see, then runs a
          worked example with numbered callouts so you can read the result with
          context.
        </p>
        <p className="mt-2">
          Dismiss the panel on any tab with{" "}
          <span className="font-mono text-zinc-900">Got it — hide</span> once
          you&apos;re comfortable. You can always re-show every tutorial via the{" "}
          <span className="font-semibold">Tutorials</span> toggle in the
          top-right.
        </p>
        <p className="mt-2 text-zinc-600">
          The tool is dense on purpose — these tutorials are how you get past
          that first wall.
        </p>
      </>
    ),
  },
];

export function FirstRunTour({ forceOpen, onClose }: Props) {
  // Open state is the union of "force-open" and "first-run".
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  // First-run detection (client-only — localStorage is unavailable during SSR).
  useEffect(() => {
    if (typeof window === "undefined") return;
    const dismissed = window.localStorage.getItem(STORAGE_KEY);
    if (!dismissed) setOpen(true);
  }, []);

  useEffect(() => {
    if (forceOpen) {
      setOpen(true);
      setStep(0);
    }
  }, [forceOpen]);

  function dismiss() {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, "1");
    }
    setOpen(false);
    setStep(0);
    onClose?.();
  }

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (!o) dismiss();
        else setOpen(true);
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[92vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white p-6 shadow-xl">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{current.emoji}</span>
              <Dialog.Title
                className="text-base font-semibold text-zinc-900"
                dangerouslySetInnerHTML={{ __html: current.title }}
              />
            </div>
            <Dialog.Close
              className="rounded-md p-1 text-zinc-500 transition hover:bg-zinc-100"
              aria-label="Close tour"
            >
              ×
            </Dialog.Close>
          </div>

          <div className="text-sm leading-relaxed text-zinc-700">
            {current.body}
          </div>

          <div className="mt-6 flex items-center justify-between">
            <div className="flex gap-1.5">
              {STEPS.map((_, i) => (
                <span
                  key={i}
                  className={`h-1.5 w-6 rounded-full transition ${
                    i === step ? "bg-zinc-900" : "bg-zinc-200"
                  }`}
                />
              ))}
            </div>
            <div className="flex gap-2">
              {step > 0 && (
                <button
                  type="button"
                  onClick={() => setStep(step - 1)}
                  className="rounded-lg border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 transition hover:bg-zinc-50"
                >
                  Back
                </button>
              )}
              {!isLast ? (
                <button
                  type="button"
                  onClick={() => setStep(step + 1)}
                  className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-zinc-800"
                >
                  Next
                </button>
              ) : (
                <button
                  type="button"
                  onClick={dismiss}
                  className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-zinc-800"
                >
                  Got it
                </button>
              )}
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
