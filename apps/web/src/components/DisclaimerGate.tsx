"use client";

/**
 * Mandatory disclaimer-accept gate.
 *
 * Shows on first visit; requires the user to tick a checkbox + click
 * "I understand" before they can use the app. Persisted in localStorage so
 * the gate only fires once per device.
 *
 * This is the legal load-bearing surface for Phase 7's trader pivot —
 * recommending specific securities or hedge baskets to individuals
 * touches regulated-advice territory in UK (FSMA/FCA), US (SEC RIA), and
 * EU (MiFID II). The gate frames every output as educational / informational
 * and forces acknowledgement before use.
 *
 * If the user dismisses without accepting (Escape, overlay click), the
 * gate re-opens on the next interaction. There is no way to bypass it.
 */

import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";

const STORAGE_KEY = "tce.disclaimer_accepted_v1";

interface Props {
  /** Optional callback fired after acceptance — page.tsx uses this to
   *  reveal the rest of the UI. */
  onAccepted?: () => void;
}

export function DisclaimerGate({ onAccepted }: Props) {
  // SSR-safe: don't read localStorage on the first render. The effect below
  // syncs after hydration.
  const [open, setOpen] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const accepted = window.localStorage.getItem(STORAGE_KEY) === "1";
    if (!accepted) setOpen(true);
    else onAccepted?.();
  }, [onAccepted]);

  function accept() {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, "1");
    }
    setOpen(false);
    onAccepted?.();
  }

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        // Block close attempts that aren't acceptance — re-open immediately.
        if (!o && open) setOpen(true);
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-[92vw] max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col overflow-y-auto rounded-2xl bg-white p-5 shadow-xl sm:p-6"
          // Prevent Escape + click-outside from closing the gate.
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <Dialog.Title className="text-base font-semibold text-zinc-900">
            Before you continue
          </Dialog.Title>
          <Dialog.Description className="mt-2 text-sm leading-relaxed text-zinc-700">
            This tool is an{" "}
            <span className="font-semibold">
              educational calculation engine
            </span>
            , not an investment advisor. It uses public market data and
            mathematical models to estimate option prices, portfolio risk, and
            historical correlations.
          </Dialog.Description>

          <div className="mt-4 space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p>
              <span className="font-semibold">Not investment advice.</span>{" "}
              Nothing here constitutes a personal recommendation, a solicitation
              to buy or sell any security, or guidance about suitability of any
              trade for you specifically.
            </p>
            <p>
              <span className="font-semibold">No guarantees.</span> Past
              performance does not predict future returns. Historical
              correlations and hedge relationships can — and do — break in new
              market regimes. Numerical results carry sampling error and model
              risk.
            </p>
            <p>
              <span className="font-semibold">You are responsible</span> for any
              trading decisions you make. Consult a licensed financial advisor
              (UK: FCA-authorised; US: SEC/state-registered RIA; EU: MiFID II
              authorised) before acting on anything you see here.
            </p>
          </div>

          <label className="mt-5 flex items-start gap-2 text-sm text-zinc-800">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-zinc-400"
            />
            <span>
              I understand this tool is for educational and informational
              purposes only, that nothing here is investment advice, and that I
              am responsible for my own trading decisions.
            </span>
          </label>

          <button
            type="button"
            disabled={!checked}
            onClick={accept}
            className="mt-5 w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            I understand — let me in
          </button>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
