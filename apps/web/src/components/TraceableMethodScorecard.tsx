"use client";

/**
 * Method scorecard + trace drawer, glued together.
 *
 * Each row click opens the VerificationTraceDrawer focused on that
 * method_id. Keeps drawer state local so individual result cards stay
 * declarative — they just hand over the FinalAnswer.
 */

import { useState } from "react";
import type { FinalAnswer } from "@/lib/types";
import { MethodScorecard } from "./MethodScorecard";
import { VerificationTraceDrawer } from "./VerificationTraceDrawer";

interface Props {
  answer: FinalAnswer;
  valueFormatter?: (v: number) => string;
}

export function TraceableMethodScorecard({ answer, valueFormatter }: Props) {
  const [open, setOpen] = useState(false);
  const [focusMethodId, setFocusMethodId] = useState<string | null>(null);

  return (
    <>
      <MethodScorecard
        per_method_status={answer.verification.per_method_status}
        valueFormatter={valueFormatter}
        onMethodClick={(id) => {
          setFocusMethodId(id);
          setOpen(true);
        }}
      />
      <div className="mt-2 text-right">
        <button
          type="button"
          onClick={() => {
            setFocusMethodId(null);
            setOpen(true);
          }}
          className="text-[11px] font-medium text-indigo-700 underline-offset-2 hover:underline"
        >
          Show full verification trace →
        </button>
      </div>
      <VerificationTraceDrawer
        open={open}
        onClose={() => setOpen(false)}
        answer={answer}
        focusMethodId={focusMethodId}
      />
    </>
  );
}

/**
 * Simple-mode counterpart: just the "Show me how this was verified" link
 * + drawer. Used by result cards when full scorecard is hidden but the
 * trace surface should still be reachable in one click.
 */
export function SimpleVerificationLink({ answer }: { answer: FinalAnswer }) {
  const [open, setOpen] = useState(false);
  const methodCount = answer.verification.per_method_status.filter(
    (r) => r.ran,
  ).length;
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 text-xs font-medium text-indigo-700 underline-offset-2 hover:underline"
      >
        🔎 Show me how this was verified
        {methodCount > 0 && (
          <span className="text-zinc-500">
            ({methodCount} method{methodCount === 1 ? "" : "s"})
          </span>
        )}
      </button>
      <VerificationTraceDrawer
        open={open}
        onClose={() => setOpen(false)}
        answer={answer}
        focusMethodId={null}
      />
    </>
  );
}
