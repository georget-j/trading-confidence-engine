"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

export type TutorialTab = "options" | "risk" | "portfolio" | "backtest";

export type GlobalOverride = "show" | "hide" | null;

const PER_TAB_STORAGE_KEY: Record<TutorialTab, string> = {
  options: "tce.tutorial_dismissed_options",
  risk: "tce.tutorial_dismissed_risk",
  portfolio: "tce.tutorial_dismissed_portfolio",
  backtest: "tce.tutorial_dismissed_backtest",
};

const GLOBAL_OVERRIDE_KEY = "tce.tutorial_global_override";

// Pub-sub for cross-component re-render after we mutate localStorage.
type Listener = () => void;
const listeners = new Set<Listener>();
function notify() {
  for (const l of listeners) l();
}
function subscribe(cb: Listener) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

function readDismissedClient(): Record<TutorialTab, boolean> {
  return {
    options: window.localStorage.getItem(PER_TAB_STORAGE_KEY.options) === "1",
    risk: window.localStorage.getItem(PER_TAB_STORAGE_KEY.risk) === "1",
    portfolio:
      window.localStorage.getItem(PER_TAB_STORAGE_KEY.portfolio) === "1",
    backtest: window.localStorage.getItem(PER_TAB_STORAGE_KEY.backtest) === "1",
  };
}

function readGlobalOverrideClient(): GlobalOverride {
  const stored = window.localStorage.getItem(GLOBAL_OVERRIDE_KEY);
  return stored === "show" || stored === "hide" ? stored : null;
}

const SSR_DISMISSED: Record<TutorialTab, boolean> = {
  options: false,
  risk: false,
  portfolio: false,
  backtest: false,
};

// Cache the snapshot so useSyncExternalStore's referential-equality check is
// satisfied between renders that haven't mutated state.
let cachedDismissed: Record<TutorialTab, boolean> = SSR_DISMISSED;
let cachedOverride: GlobalOverride = null;
let cacheHydrated = false;

function snapshotDismissed(): Record<TutorialTab, boolean> {
  if (!cacheHydrated && typeof window !== "undefined") {
    cachedDismissed = readDismissedClient();
    cachedOverride = readGlobalOverrideClient();
    cacheHydrated = true;
  }
  return cachedDismissed;
}

function snapshotOverride(): GlobalOverride {
  snapshotDismissed(); // ensures cacheHydrated
  return cachedOverride;
}

function getServerDismissed(): Record<TutorialTab, boolean> {
  return SSR_DISMISSED;
}

function getServerOverride(): GlobalOverride {
  return null;
}

function refresh() {
  if (typeof window === "undefined") return;
  cachedDismissed = readDismissedClient();
  cachedOverride = readGlobalOverrideClient();
  cacheHydrated = true;
  notify();
}

interface TutorialContextValue {
  isExpanded: (tab: TutorialTab) => boolean;
  dismiss: (tab: TutorialTab) => void;
  reopen: (tab: TutorialTab) => void;
  globalOverride: GlobalOverride;
  setGlobalOverride: (value: GlobalOverride) => void;
}

const TutorialContext = createContext<TutorialContextValue | null>(null);

interface ProviderProps {
  children: ReactNode;
}

export function TutorialProvider({ children }: ProviderProps) {
  const dismissedTabs = useSyncExternalStore(
    subscribe,
    snapshotDismissed,
    getServerDismissed,
  );
  const globalOverride = useSyncExternalStore(
    subscribe,
    snapshotOverride,
    getServerOverride,
  );

  const dismiss = useCallback((tab: TutorialTab) => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(PER_TAB_STORAGE_KEY[tab], "1");
    refresh();
  }, []);

  const reopen = useCallback((tab: TutorialTab) => {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(PER_TAB_STORAGE_KEY[tab]);
    refresh();
  }, []);

  const setGlobalOverride = useCallback((value: GlobalOverride) => {
    if (typeof window === "undefined") return;
    if (value === null) {
      window.localStorage.removeItem(GLOBAL_OVERRIDE_KEY);
    } else {
      window.localStorage.setItem(GLOBAL_OVERRIDE_KEY, value);
    }
    refresh();
  }, []);

  const isExpanded = useCallback(
    (tab: TutorialTab) => {
      if (globalOverride === "hide") return false;
      if (globalOverride === "show") return true;
      return !dismissedTabs[tab];
    },
    [globalOverride, dismissedTabs],
  );

  const value = useMemo<TutorialContextValue>(
    () => ({
      isExpanded,
      dismiss,
      reopen,
      globalOverride,
      setGlobalOverride,
    }),
    [isExpanded, dismiss, reopen, globalOverride, setGlobalOverride],
  );

  return (
    <TutorialContext.Provider value={value}>
      {children}
    </TutorialContext.Provider>
  );
}

export function useTutorial(): TutorialContextValue {
  const ctx = useContext(TutorialContext);
  if (!ctx) {
    throw new Error("useTutorial must be used inside <TutorialProvider>");
  }
  return ctx;
}
