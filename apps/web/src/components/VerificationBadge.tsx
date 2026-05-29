"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { VERIFICATION_STATUS } from "@/lib/copy";
import type { VerificationStatus } from "@/lib/types";

/**
 * Status pills always carry both an icon (color-blind safe) AND a text
 * label so colour is never the sole carrier of meaning. Improves a11y +
 * scannability for new users.
 */
const STYLES: Record<
  VerificationStatus,
  { label: string; icon: string; classes: string }
> = {
  verified: {
    label: "Verified",
    icon: "✓",
    classes:
      "bg-emerald-100 text-emerald-900 ring-emerald-300 hover:bg-emerald-200",
  },
  partially_verified: {
    label: "Partially verified",
    icon: "⚠",
    classes: "bg-amber-100 text-amber-900 ring-amber-300 hover:bg-amber-200",
  },
  not_verified: {
    label: "Not verified",
    icon: "✗",
    classes: "bg-rose-100 text-rose-900 ring-rose-300 hover:bg-rose-200",
  },
};

const WORKED_EXAMPLE = {
  inputs: "SPY 450 call, 30 days, 18% IV, 5% rate, 1.3% dividend",
  steps: [
    {
      title: "1. Two independent calculators run",
      body: "py_vollib computes the Black-Scholes-Merton closed-form price ($9.94). QuantLib computes the same option via a Leisen-Reimer binomial tree ($9.94). Different codebases, different algorithms.",
    },
    {
      title: "2. The verifier compares them",
      body: "If they agree within tolerance (1e-3 absolute or 1e-4 relative on price), method_agreement_score = 1.0. Otherwise the answer is flagged.",
    },
    {
      title: "3. No-arbitrage invariants are checked",
      body: "Call price ≥ max(S·e^{-qT} − K·e^{-rT}, 0). Call price ≤ S·e^{-qT}. Delta in [0, 1]. Gamma ≥ 0. Any failure hard-fails to not_verified.",
    },
    {
      title: "4. Status is decided",
      body: "Verified if both methods agreed AND every invariant passed AND inputs were complete. Otherwise partially_verified or not_verified, with the reason surfaced as a limitation.",
    },
  ],
};

interface Props {
  status: VerificationStatus;
}

export function VerificationBadge({ status }: Props) {
  const s = STYLES[status];
  const meta = VERIFICATION_STATUS[status];

  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button
          type="button"
          aria-label={`Verification status: ${s.label}. Click for details.`}
          className={`inline-flex cursor-pointer items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset transition ${s.classes}`}
        >
          <span aria-hidden className="text-sm leading-none">
            {s.icon}
          </span>
          {s.label}
          <span className="ml-0.5 inline-flex h-4 w-4 items-center justify-center rounded-full bg-white/40 text-[10px]">
            ?
          </span>
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[92vw] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl bg-white p-4 shadow-xl sm:p-6">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-base font-semibold text-zinc-900">
                What does &ldquo;{meta.label}&rdquo; mean?
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm leading-relaxed text-zinc-700">
                {meta.info}
              </Dialog.Description>
            </div>
            <Dialog.Close
              className="-mr-2 -mt-2 inline-flex h-11 w-11 items-center justify-center rounded-md text-2xl leading-none text-zinc-500 transition hover:bg-zinc-100"
              aria-label="Close"
            >
              ×
            </Dialog.Close>
          </div>

          <div className="border-t border-zinc-200 pt-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Worked example
            </div>
            <div className="mt-1 text-xs text-zinc-600">
              Inputs:{" "}
              <span className="font-mono text-zinc-900">
                {WORKED_EXAMPLE.inputs}
              </span>
            </div>
            <div className="mt-3 space-y-3">
              {WORKED_EXAMPLE.steps.map((step) => (
                <div key={step.title}>
                  <div className="text-xs font-semibold text-zinc-900">
                    {step.title}
                  </div>
                  <p className="mt-0.5 text-xs leading-relaxed text-zinc-600">
                    {step.body}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
            <span className="font-semibold text-zinc-700">Important:</span>{" "}
            &ldquo;Verified&rdquo; means the model and calculators are
            self-consistent — not that the market will behave this way. Always
            apply your own judgment. Not investment advice.
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
