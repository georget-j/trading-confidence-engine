"use client";

import { useState } from "react";
import { BacktestForm } from "@/components/BacktestForm";
import { BacktestResultCard } from "@/components/BacktestResultCard";
import { ChatPanel } from "@/components/ChatPanel";
import { Compare } from "@/components/Compare";
import { DisclaimerGate } from "@/components/DisclaimerGate";
import { FirstRunTour } from "@/components/FirstRunTour";
import { Glossary } from "@/components/Glossary";
import { HedgeFinder } from "@/components/HedgeFinder";
import { Home as HomePanel, type HomeDestination } from "@/components/Home";
import { Methods } from "@/components/Methods";
import { MethodsLab } from "@/components/MethodsLab";
import { MyPortfolio } from "@/components/MyPortfolio";
import { PortfolioForm } from "@/components/PortfolioForm";
import { PortfolioResultCard } from "@/components/PortfolioResultCard";
import { SavedWorkflows } from "@/components/SavedWorkflows";
import {
  DEFAULT_FORM_STATE,
  formStateFromRequest,
  PricingForm,
  type PricingFormState,
} from "@/components/PricingForm";
import { ResultCard } from "@/components/ResultCard";
import { RiskForm } from "@/components/RiskForm";
import { RiskResultCard } from "@/components/RiskResultCard";
import { StrategyForm } from "@/components/StrategyForm";
import { StrategyResultCard } from "@/components/StrategyResultCard";
import { TradeIdeas } from "@/components/TradeIdeas";
import { TutorialPanel, TutorialToggle } from "@/components/TutorialPanel";
import type { SavedWorkflow } from "@/lib/workflows";
import {
  computeVaR,
  optimizePortfolio,
  priceOption,
  priceStrategy,
  runBacktest,
} from "@/lib/api";
import {
  SimpleModeProvider,
  SimpleModeToggle,
  useSimpleMode,
} from "@/lib/simple-mode";
import { TutorialProvider } from "@/lib/tutorial";
import {
  buildBacktestTutorialConfig,
  buildOptionsTutorialConfig,
  buildPortfolioTutorialConfig,
  buildRiskTutorialConfig,
} from "@/lib/tutorial-configs";
import {
  BACKTEST_FIXTURE,
  OPTIONS_FIXTURE,
  PORTFOLIO_FIXTURE,
  VAR_FIXTURE,
} from "@/lib/tutorial-fixtures";
import type {
  BacktestRequest,
  FinalAnswer,
  OptionsPricingRequest,
  OptionsStrategyRequest,
  PortfolioRequest,
  VaRRequest,
} from "@/lib/types";

/** Top-level navigation — Home (deliberate landing page) leads, then four
 *  trader workflows, with the original verification surface tucked under
 *  the "Calculators" tab so the engineering portfolio audience can still
 *  reach it. */
type TopTab =
  | "home"
  | "trade_ideas"
  | "my_portfolio"
  | "hedge_finder"
  | "compare"
  | "calculators";
/** Sub-tab inside the Calculators tab — wraps the original four educational
 *  surfaces plus the Methods Lab. */
type CalcTab = "options" | "risk" | "portfolio" | "backtest" | "lab";
type OptionsMode = "single" | "strategy";

export default function Home() {
  const [topTab, setTopTab] = useState<TopTab>("home");
  const [tab, setTab] = useState<CalcTab>("options");
  const [optionsMode, setOptionsMode] = useState<OptionsMode>("single");

  /** Jump straight to a specific calculator sub-tab. */
  function openCalculator(sub: CalcTab) {
    setTopTab("calculators");
    setTab(sub);
  }

  /** Home card click → jump to the chosen trader tab. */
  function handleHomePick(destination: HomeDestination) {
    setTopTab(destination);
  }

  // Per-tab state — kept separate so switching tabs doesn't wipe the other side.
  const [optionsState, setOptionsState] =
    useState<PricingFormState>(DEFAULT_FORM_STATE);
  const [optionsAnswer, setOptionsAnswer] = useState<FinalAnswer | null>(null);
  const [optionsRequest, setOptionsRequest] =
    useState<OptionsPricingRequest | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [highlightForm, setHighlightForm] = useState(false);

  // Strategy mode lives in its own state slot so switching back to single-leg
  // preserves the result, and vice versa.
  const [strategyAnswer, setStrategyAnswer] = useState<FinalAnswer | null>(
    null,
  );
  const [strategyRequest, setStrategyRequest] =
    useState<OptionsStrategyRequest | null>(null);
  const [strategyLoading, setStrategyLoading] = useState(false);
  const [strategyError, setStrategyError] = useState<string | null>(null);

  const [riskAnswer, setRiskAnswer] = useState<FinalAnswer | null>(null);
  const [riskRequest, setRiskRequest] = useState<VaRRequest | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState<string | null>(null);

  const [portfolioAnswer, setPortfolioAnswer] = useState<FinalAnswer | null>(
    null,
  );
  const [portfolioRequest, setPortfolioRequest] =
    useState<PortfolioRequest | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);

  const [backtestAnswer, setBacktestAnswer] = useState<FinalAnswer | null>(
    null,
  );
  const [backtestRequest, setBacktestRequest] =
    useState<BacktestRequest | null>(null);
  const [backtestCapital, setBacktestCapital] = useState(10_000);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestError, setBacktestError] = useState<string | null>(null);

  // Tour can be re-opened from the header "Help" link even after it's been
  // dismissed (localStorage flag stays set; we just re-render with a new key).
  const [tourReopenKey, setTourReopenKey] = useState(0);

  // Per-tab "has the worked example been run" — drives whether the tutorial
  // panel shows its result-side callouts.
  const [optionsExampleRan, setOptionsExampleRan] = useState(false);
  const [riskExampleRan, setRiskExampleRan] = useState(false);
  const [portfolioExampleRan, setPortfolioExampleRan] = useState(false);
  const [backtestExampleRan, setBacktestExampleRan] = useState(false);

  // Tutorial worked-example handlers — set fixture answer/request directly so
  // the example is deterministic and works offline.
  function runOptionsExample() {
    setOptionsMode("single");
    setOptionsState(formStateFromRequest(OPTIONS_FIXTURE.request));
    setOptionsAnswer(OPTIONS_FIXTURE.answer);
    setOptionsRequest(OPTIONS_FIXTURE.request);
    setOptionsError(null);
    setOptionsExampleRan(true);
  }
  function runRiskExample() {
    setRiskAnswer(VAR_FIXTURE.answer);
    setRiskRequest(VAR_FIXTURE.request);
    setRiskError(null);
    setRiskExampleRan(true);
  }
  function runPortfolioExample() {
    setPortfolioAnswer(PORTFOLIO_FIXTURE.answer);
    setPortfolioRequest(PORTFOLIO_FIXTURE.request);
    setPortfolioError(null);
    setPortfolioExampleRan(true);
  }
  function runBacktestExample() {
    setBacktestAnswer(BACKTEST_FIXTURE.answer);
    setBacktestRequest(BACKTEST_FIXTURE.request);
    setBacktestCapital(BACKTEST_FIXTURE.request.initial_capital ?? 10_000);
    setBacktestError(null);
    setBacktestExampleRan(true);
  }

  const optionsTutorial = buildOptionsTutorialConfig({
    onRun: runOptionsExample,
    hasRun: optionsExampleRan,
  });
  const riskTutorial = buildRiskTutorialConfig({
    onRun: runRiskExample,
    hasRun: riskExampleRan,
  });
  const portfolioTutorial = buildPortfolioTutorialConfig({
    onRun: runPortfolioExample,
    hasRun: portfolioExampleRan,
  });
  const backtestTutorial = buildBacktestTutorialConfig({
    onRun: runBacktestExample,
    hasRun: backtestExampleRan,
  });

  async function handlePriceOption(req: OptionsPricingRequest) {
    setOptionsError(null);
    setOptionsLoading(true);
    try {
      const result = await priceOption(req);
      setOptionsAnswer(result);
      setOptionsRequest(req);
    } catch (e) {
      setOptionsError(e instanceof Error ? e.message : String(e));
      setOptionsAnswer(null);
      setOptionsRequest(null);
    } finally {
      setOptionsLoading(false);
    }
  }

  async function handlePriceStrategy(req: OptionsStrategyRequest) {
    setStrategyError(null);
    setStrategyLoading(true);
    try {
      const result = await priceStrategy(req);
      setStrategyAnswer(result);
      setStrategyRequest(req);
    } catch (e) {
      setStrategyError(e instanceof Error ? e.message : String(e));
      setStrategyAnswer(null);
      setStrategyRequest(null);
    } finally {
      setStrategyLoading(false);
    }
  }

  function handleChatParsed(req: OptionsPricingRequest) {
    setOptionsState(formStateFromRequest(req));
    setHighlightForm(true);
    window.setTimeout(() => setHighlightForm(false), 1500);
  }

  async function handleComputeVaR(req: VaRRequest) {
    setRiskError(null);
    setRiskLoading(true);
    try {
      const result = await computeVaR(req);
      setRiskAnswer(result);
      setRiskRequest(req);
    } catch (e) {
      setRiskError(e instanceof Error ? e.message : String(e));
      setRiskAnswer(null);
      setRiskRequest(null);
    } finally {
      setRiskLoading(false);
    }
  }

  async function handleOptimizePortfolio(req: PortfolioRequest) {
    setPortfolioError(null);
    setPortfolioLoading(true);
    try {
      const result = await optimizePortfolio(req);
      setPortfolioAnswer(result);
      setPortfolioRequest(req);
    } catch (e) {
      setPortfolioError(e instanceof Error ? e.message : String(e));
      setPortfolioAnswer(null);
      setPortfolioRequest(null);
    } finally {
      setPortfolioLoading(false);
    }
  }

  function handleLoadWorkflow(wf: SavedWorkflow) {
    // Saved workflows always belong to a Calculators sub-tab; jump there.
    setTopTab("calculators");
    if (wf.family === "options") {
      setTab("options");
      const req = wf.payload as OptionsPricingRequest;
      setOptionsState(formStateFromRequest(req));
      handlePriceOption(req);
    } else if (wf.family === "risk") {
      setTab("risk");
      handleComputeVaR(wf.payload as VaRRequest);
    } else if (wf.family === "portfolio") {
      setTab("portfolio");
      handleOptimizePortfolio(wf.payload as PortfolioRequest);
    } else if (wf.family === "backtest") {
      setTab("backtest");
      handleRunBacktest(wf.payload as BacktestRequest);
    }
  }

  async function handleRunBacktest(req: BacktestRequest) {
    setBacktestError(null);
    setBacktestLoading(true);
    setBacktestCapital(req.initial_capital ?? 10_000);
    try {
      const result = await runBacktest(req);
      setBacktestAnswer(result);
      setBacktestRequest(req);
    } catch (e) {
      setBacktestError(e instanceof Error ? e.message : String(e));
      setBacktestAnswer(null);
      setBacktestRequest(null);
    } finally {
      setBacktestLoading(false);
    }
  }

  // Disclaimer acceptance — drives whether the persistent amber banner is
  // shown (pre-accept) or collapsed to a tiny "Educational use" pill in the
  // nav (post-accept). Reduces banner fatigue while keeping the framing
  // permanently visible.
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);

  return (
    <TutorialProvider>
      <SimpleModeProvider>
        <main className="min-h-dvh bg-zinc-50">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-12">
            <header className="mb-6 flex flex-col gap-4 sm:mb-8 md:flex-row md:items-start md:justify-between md:gap-6">
              <div>
                <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl">
                  Trading Confidence Engine
                </h1>
                <p className="mt-1 max-w-2xl text-xs text-zinc-600 sm:text-sm">
                  Look up real stocks, analyse a portfolio, find hedges — every
                  number cross-verified by independent methods.
                </p>
              </div>
              <nav className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs md:shrink-0 md:pt-2">
                <SimpleModeToggle />
                {disclaimerAccepted && (
                  <span
                    className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-800"
                    title="This is an educational calculation engine, not investment advice. Consult a licensed advisor before acting on any output."
                  >
                    ⓘ Not advice
                  </span>
                )}
                <SavedWorkflows onLoad={handleLoadWorkflow} />
                <Methods />
                <Glossary />
                <TutorialToggle />
                <button
                  type="button"
                  onClick={() => setTourReopenKey((k) => k + 1)}
                  className="font-medium text-zinc-600 transition hover:text-zinc-900"
                >
                  Tour
                </button>
              </nav>
            </header>

            <DisclaimerGate onAccepted={() => setDisclaimerAccepted(true)} />
            <FirstRunTour key={tourReopenKey} forceOpen={tourReopenKey > 0} />

            {/* Pre-acceptance: a loud banner reinforcing the modal. Post-
              acceptance: the small "Not advice" pill in the nav above is
              enough, plus the footer text. */}
            {!disclaimerAccepted && (
              <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] leading-relaxed text-amber-900 sm:text-xs">
                <span className="font-semibold uppercase tracking-wide">
                  Educational use only
                </span>
                {" — "}
                this is a calculation engine, not investment advice. Nothing
                here is a personal recommendation; consult a licensed advisor
                before acting on any output.
              </div>
            )}

            {/* Top-level tab bar: trader workflows first, the original
              verification surfaces tucked under Calculators. Scrolls
              horizontally on narrow screens to keep the pill row visually
              a single unit. */}
            <div className="mb-6 -mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0 sm:overflow-visible">
              <div className="inline-flex rounded-lg border border-zinc-300 bg-white p-0.5 shadow-sm">
                <TabButton
                  active={topTab === "home"}
                  onClick={() => setTopTab("home")}
                >
                  Home
                </TabButton>
                <TabButton
                  active={topTab === "trade_ideas"}
                  onClick={() => setTopTab("trade_ideas")}
                >
                  Trade ideas
                </TabButton>
                <TabButton
                  active={topTab === "my_portfolio"}
                  onClick={() => setTopTab("my_portfolio")}
                >
                  My portfolio
                </TabButton>
                <TabButton
                  active={topTab === "hedge_finder"}
                  onClick={() => setTopTab("hedge_finder")}
                >
                  Hedge finder
                </TabButton>
                <TabButton
                  active={topTab === "compare"}
                  onClick={() => setTopTab("compare")}
                >
                  Compare
                </TabButton>
                <TabButton
                  active={topTab === "calculators"}
                  onClick={() => setTopTab("calculators")}
                >
                  Calculators
                </TabButton>
              </div>
            </div>

            {/* Trader-tab destinations. Home (default) → user picks one →
              corresponding tab renders. */}
            {topTab === "home" && <HomePanel onPick={handleHomePick} />}
            {topTab === "trade_ideas" && (
              <TradeIdeas onOpenCalculators={() => openCalculator("lab")} />
            )}
            {topTab === "my_portfolio" && (
              <MyPortfolio
                onOpenCalculators={() => openCalculator("portfolio")}
              />
            )}
            {topTab === "hedge_finder" && (
              <HedgeFinder
                onOpenCalculators={() => openCalculator("backtest")}
              />
            )}
            {topTab === "compare" && (
              <Compare onOpenCalculators={() => openCalculator("lab")} />
            )}

            {topTab === "calculators" && (
              <div className="mb-4 -mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0 sm:overflow-visible">
                <div className="inline-flex rounded-lg border border-zinc-300 bg-white p-0.5 shadow-sm">
                  <TabButton
                    active={tab === "options"}
                    onClick={() => setTab("options")}
                  >
                    Options pricing
                  </TabButton>
                  <TabButton
                    active={tab === "risk"}
                    onClick={() => setTab("risk")}
                  >
                    Value at Risk
                  </TabButton>
                  <TabButton
                    active={tab === "portfolio"}
                    onClick={() => setTab("portfolio")}
                  >
                    Portfolio
                  </TabButton>
                  <TabButton
                    active={tab === "backtest"}
                    onClick={() => setTab("backtest")}
                  >
                    Backtest
                  </TabButton>
                  <TabButton
                    active={tab === "lab"}
                    onClick={() => setTab("lab")}
                  >
                    Methods Lab
                  </TabButton>
                </div>
              </div>
            )}

            {topTab === "calculators" && tab === "options" && (
              <div className="space-y-4">
                <TutorialPanel config={optionsTutorial} />
                <div className="inline-flex rounded-lg border border-zinc-300 bg-white p-0.5 shadow-sm">
                  <ModeButton
                    active={optionsMode === "single"}
                    onClick={() => setOptionsMode("single")}
                  >
                    Single leg
                  </ModeButton>
                  <ModeButton
                    active={optionsMode === "strategy"}
                    onClick={() => setOptionsMode("strategy")}
                  >
                    Strategy (multi-leg)
                  </ModeButton>
                </div>

                {optionsMode === "single" ? (
                  <div className="grid gap-6 lg:grid-cols-[1fr_1fr_1.2fr]">
                    <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
                      <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                        Chat input
                      </h2>
                      <ChatPanel family="options" onParsed={handleChatParsed} />
                    </section>

                    <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
                      <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                        European option
                      </h2>
                      <PricingForm
                        state={optionsState}
                        onChange={setOptionsState}
                        onSubmit={handlePriceOption}
                        loading={optionsLoading}
                        highlight={highlightForm}
                      />
                    </section>

                    <ResultSection
                      loading={optionsLoading}
                      error={optionsError}
                      empty="Enter inputs and price an option."
                      emptyDetail="py_vollib closed-form and QuantLib Leisen-Reimer binomial run, then a cross-method verifier and no-arbitrage invariants decide the status."
                    >
                      {optionsAnswer && (
                        <ResultCard
                          answer={optionsAnswer}
                          request={optionsRequest ?? undefined}
                        />
                      )}
                    </ResultSection>
                  </div>
                ) : (
                  <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
                    <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
                      <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                        Multi-leg strategy
                      </h2>
                      <StrategyForm
                        onSubmit={handlePriceStrategy}
                        loading={strategyLoading}
                      />
                    </section>

                    <ResultSection
                      loading={strategyLoading}
                      error={strategyError}
                      empty="Compose 2–4 legs and price the strategy."
                      emptyDetail="Each leg is priced independently by BSM closed-form and QuantLib binomial. Verification requires per-leg agreement — opposite-sign legs can't hide drift in the net premium."
                    >
                      {strategyAnswer && (
                        <StrategyResultCard
                          answer={strategyAnswer}
                          request={strategyRequest ?? undefined}
                        />
                      )}
                    </ResultSection>
                  </div>
                )}
              </div>
            )}

            {topTab === "calculators" && tab === "risk" && (
              <>
                <TutorialPanel config={riskTutorial} />
                <div className="grid gap-6 lg:grid-cols-[1fr_1fr_1.5fr]">
                  <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
                    <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                      Chat input
                    </h2>
                    <ChatPanel
                      family="var"
                      onParsed={(req) => handleComputeVaR(req)}
                    />
                  </section>

                  <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
                    <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                      VaR / CVaR
                    </h2>
                    <RiskForm
                      onSubmit={handleComputeVaR}
                      loading={riskLoading}
                    />
                  </section>

                  <ResultSection
                    loading={riskLoading}
                    error={riskError}
                    empty="Pick a ticker and compute VaR."
                    emptyDetail="Three independent methods (historical, parametric, Monte Carlo) cross-verified. Divergence between methods becomes a signal about fat tails in the data."
                  >
                    {riskAnswer && (
                      <RiskResultCard
                        answer={riskAnswer}
                        request={riskRequest ?? undefined}
                      />
                    )}
                  </ResultSection>
                </div>
              </>
            )}

            {topTab === "calculators" && tab === "portfolio" && (
              <>
                <TutorialPanel config={portfolioTutorial} />
                <div className="grid gap-6 lg:grid-cols-[1fr_1fr_1.5fr]">
                  <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
                    <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                      Chat input
                    </h2>
                    <ChatPanel
                      family="portfolio"
                      onParsed={(req) => handleOptimizePortfolio(req)}
                    />
                  </section>

                  <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
                    <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                      Portfolio optimisation
                    </h2>
                    <PortfolioForm
                      onSubmit={handleOptimizePortfolio}
                      loading={portfolioLoading}
                    />
                  </section>

                  <ResultSection
                    loading={portfolioLoading}
                    error={portfolioError}
                    empty="Pick a basket of tickers and optimise."
                    emptyDetail="Convex QP gives the optimal weights. Verification checks KKT conditions, cross-solver agreement, and how much the weights move under small input perturbations — a fragile optimum is honest about being one."
                  >
                    {portfolioAnswer && (
                      <PortfolioResultCard
                        answer={portfolioAnswer}
                        request={portfolioRequest ?? undefined}
                      />
                    )}
                  </ResultSection>
                </div>
              </>
            )}

            {topTab === "calculators" && tab === "backtest" && (
              <>
                <TutorialPanel config={backtestTutorial} />
                <div className="grid gap-6 lg:grid-cols-[1fr_1fr_1.5fr]">
                  <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
                    <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                      Chat input
                    </h2>
                    <ChatPanel
                      family="backtest"
                      onParsed={(req) => handleRunBacktest(req)}
                    />
                  </section>

                  <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
                    <h2 className="mb-4 text-sm font-semibold text-zinc-900">
                      Backtest
                    </h2>
                    <BacktestForm
                      onSubmit={handleRunBacktest}
                      loading={backtestLoading}
                    />
                  </section>

                  <ResultSection
                    loading={backtestLoading}
                    error={backtestError}
                    empty="Pick a ticker and strategy."
                    emptyDetail="Three strategies, configurable slippage, walk-forward reproducibility check, look-ahead bias detector, and a buy-and-hold benchmark for honest alpha comparison."
                  >
                    {backtestAnswer && (
                      <BacktestResultCard
                        answer={backtestAnswer}
                        initialCapital={backtestCapital}
                        request={backtestRequest ?? undefined}
                      />
                    )}
                  </ResultSection>
                </div>
              </>
            )}

            {topTab === "calculators" && tab === "lab" && (
              <div className="space-y-4">
                <section className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-4 shadow-sm sm:p-6">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-indigo-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                      Lab
                    </span>
                    <h2 className="text-sm font-semibold text-zinc-900">
                      Methods Lab
                    </h2>
                  </div>
                  <p className="mt-2 max-w-3xl text-xs leading-relaxed text-zinc-700 sm:text-sm">
                    Invoke any single calculator method directly with raw
                    inputs. No cross-method check, no invariants, no sensitivity
                    — just the one method&apos;s number. Useful for comparing
                    methods by hand or sanity-checking a result the orchestrated
                    pipeline marked partially verified.
                  </p>
                </section>
                <MethodsLab />
              </div>
            )}

            <footer className="mt-12 space-y-2 text-xs text-zinc-500">
              <p>
                <span className="font-semibold text-zinc-700">
                  Not investment advice.
                </span>{" "}
                This is a calculation engine for educational and analytical use.
                Outputs are based on historical data and mathematical models
                that can — and do — break in new market regimes. Consult a
                licensed financial advisor (UK: FCA-authorised; US:
                SEC/state-registered RIA; EU: MiFID II authorised) before acting
                on any output. You are responsible for your own trading
                decisions.
              </p>
            </footer>
          </div>
        </main>
      </SimpleModeProvider>
    </TutorialProvider>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
        active ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-100"
      }`}
    >
      {children}
    </button>
  );
}

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md px-3 py-1 text-xs font-medium transition ${
        active ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-100"
      }`}
    >
      {children}
    </button>
  );
}

function ResultSection({
  loading,
  error,
  empty,
  emptyDetail,
  children,
}: {
  loading: boolean;
  error: string | null;
  empty: string;
  emptyDetail: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6 shadow-sm">
      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <div className="font-semibold">Request failed</div>
          <div className="mt-1 font-mono text-xs">{error}</div>
        </div>
      )}
      {!children && !error && !loading && (
        <div className="flex h-full min-h-[420px] flex-col items-center justify-center text-center text-sm text-zinc-500">
          <div className="mb-2 text-4xl">🔍</div>
          <div className="font-medium text-zinc-700">{empty}</div>
          <div className="mt-1 max-w-xs text-xs text-zinc-500">
            {emptyDetail}
          </div>
        </div>
      )}
      {children}
    </section>
  );
}
