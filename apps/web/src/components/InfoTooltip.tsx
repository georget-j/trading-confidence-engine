"use client";

import * as Tooltip from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

interface Props {
  body: string | ReactNode;
  /** Trigger element. Defaults to a small ⓘ icon. */
  children?: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
}

export function InfoTooltip({ body, children, side = "top" }: Props) {
  return (
    <Tooltip.Provider delayDuration={150}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          {children ?? (
            <button
              type="button"
              aria-label="More information"
              className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full border border-zinc-300 text-[10px] font-semibold text-zinc-500 transition hover:border-zinc-500 hover:text-zinc-700"
            >
              i
            </button>
          )}
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side={side}
            sideOffset={6}
            className="z-50 max-w-xs rounded-lg bg-zinc-900 px-3 py-2 text-xs leading-relaxed text-zinc-100 shadow-lg ring-1 ring-zinc-800"
          >
            {body}
            <Tooltip.Arrow className="fill-zinc-900" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
