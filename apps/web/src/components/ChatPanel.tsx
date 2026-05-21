"use client";

import { useState } from "react";
import { parseChat } from "@/lib/api";
import type { LLMOptionsParse, OptionsPricingRequest } from "@/lib/types";

interface Props {
  onParsed: (req: OptionsPricingRequest, parse: LLMOptionsParse) => void;
}

const EXAMPLE_PROMPTS = [
  "SPY 450 call expiring in 30 days at 18% IV, 5% rate",
  "Price a 6-month ATM put on $100 underlying with 25% vol",
  "TSLA 200 strike call, 90 days out, 60% IV, 4% rate, no dividend",
];

export function ChatPanel({ onParsed }: Props) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastParse, setLastParse] = useState<LLMOptionsParse | null>(null);
  const [llmUnavailable, setLlmUnavailable] = useState(false);

  async function submit() {
    if (!text.trim()) return;
    setError(null);
    setLoading(true);
    setLlmUnavailable(false);
    try {
      const response = await parseChat(text);
      setLastParse(response.raw_parse);
      if (response.ready_to_price && response.structured) {
        onParsed(response.structured, response.raw_parse);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("503")) {
        setLlmUnavailable(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs font-medium text-zinc-600">
          Ask in plain English
        </label>
        <p className="mt-0.5 text-[11px] text-zinc-500">
          The LLM extracts inputs only — it does not produce prices. The form on
          the right will fill in, then you press{" "}
          <span className="font-medium text-zinc-700">Price + verify</span>.
        </p>
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKey}
        rows={3}
        placeholder="e.g. price a SPY 450 call 30 days out at 18% IV"
        className="w-full resize-none rounded-lg border border-zinc-300 bg-white p-3 text-sm text-zinc-900 outline-none transition focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
      />

      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-1">
          {EXAMPLE_PROMPTS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setText(p)}
              className="rounded-full border border-zinc-200 px-2 py-0.5 text-[10px] text-zinc-600 transition hover:border-zinc-400 hover:text-zinc-900"
            >
              {p.slice(0, 28)}…
            </button>
          ))}
        </div>
        <button
          onClick={submit}
          disabled={loading || !text.trim()}
          className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:bg-zinc-400"
        >
          {loading ? "Parsing…" : "Parse → fill form"}
        </button>
      </div>

      {llmUnavailable && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          <div className="font-semibold">Chat parser not configured</div>
          <div className="mt-1">
            Set{" "}
            <code className="rounded bg-amber-100 px-1">ANTHROPIC_API_KEY</code>{" "}
            or <code className="rounded bg-amber-100 px-1">OPENAI_API_KEY</code>{" "}
            in the API environment, then restart. The structured form on the
            right works without an LLM.
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-2 text-xs text-rose-800">
          {error}
        </div>
      )}

      {lastParse && (
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-zinc-700">LLM parse</span>
            <span className="text-zinc-500">
              confidence {(lastParse.parse_confidence * 100).toFixed(0)}%
            </span>
          </div>
          {lastParse.parser_notes.length > 0 && (
            <ul className="mt-1 list-disc space-y-0.5 pl-4 text-zinc-600">
              {lastParse.parser_notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          )}
          {lastParse.parse_confidence < 0.5 && (
            <div className="mt-1 text-rose-700">
              Missing inputs — form not auto-filled. Add what&apos;s missing and
              try again, or fill the form manually.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
