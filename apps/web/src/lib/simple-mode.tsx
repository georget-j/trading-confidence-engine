"use client";

/**
 * Simple vs Advanced mode — context + localStorage persistence.
 *
 * Simple mode is the new default for first-time visitors. It hides the
 * verification-engine metadata (per-method scorecard, invariants list,
 * trace-drawer link, full limitations boxes, secondary stat grids) so a
 * beginner sees a clean "headline + one-line summary" experience.
 *
 * Advanced mode is the original surface: every method, every invariant,
 * the full trace drawer, every stat. This is what the engineering-portfolio
 * audience expects.
 *
 * Switching modes is a single header toggle. The choice persists across
 * sessions via localStorage (`tce.mode_v1`). SSR-safe: the provider
 * starts in Simple mode on render 1 (no localStorage), then hydrates the
 * stored value on mount. That means first-paint for a returning Advanced
 * user shows Simple for a frame — acceptable because the only difference
 * is which conditional branch each result card renders.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "tce.mode_v1";

export type AppMode = "simple" | "advanced";

interface SimpleModeContextValue {
  mode: AppMode;
  setMode: (m: AppMode) => void;
  toggleMode: () => void;
  /** Convenience: true iff mode === "advanced". */
  isAdvanced: boolean;
}

const SimpleModeContext = createContext<SimpleModeContextValue | null>(null);

export function SimpleModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<AppMode>("simple");

  // Hydrate from localStorage after mount — SSR-safe.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "advanced" || stored === "simple") {
      setModeState(stored);
    }
  }, []);

  const setMode = useCallback((m: AppMode) => {
    setModeState(m);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, m);
    }
  }, []);

  const toggleMode = useCallback(() => {
    setMode(mode === "simple" ? "advanced" : "simple");
  }, [mode, setMode]);

  return (
    <SimpleModeContext.Provider
      value={{ mode, setMode, toggleMode, isAdvanced: mode === "advanced" }}
    >
      {children}
    </SimpleModeContext.Provider>
  );
}

export function useSimpleMode(): SimpleModeContextValue {
  const ctx = useContext(SimpleModeContext);
  if (ctx === null) {
    throw new Error("useSimpleMode must be used inside <SimpleModeProvider>");
  }
  return ctx;
}

/**
 * Header toggle button — drop into the existing nav row.
 */
export function SimpleModeToggle() {
  const { mode, toggleMode } = useSimpleMode();
  const label = mode === "simple" ? "Simple" : "Advanced";
  const title =
    mode === "simple"
      ? "Currently showing a beginner-friendly view. Click to switch to the full engineering surface."
      : "Currently showing the full verification metadata. Click to switch back to a beginner view.";
  return (
    <button
      type="button"
      onClick={toggleMode}
      title={title}
      aria-label={`Switch to ${mode === "simple" ? "advanced" : "simple"} mode`}
      className={`rounded-md border px-2.5 py-1 text-xs font-medium transition ${
        mode === "simple"
          ? "border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
          : "border-zinc-300 bg-zinc-50 text-zinc-700 hover:bg-zinc-100"
      }`}
    >
      View: {label}
    </button>
  );
}
