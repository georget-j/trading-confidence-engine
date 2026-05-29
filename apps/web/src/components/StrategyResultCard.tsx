import { GREEKS, STRATEGY_OUTPUTS } from "@/lib/copy";
import type {
  FinalAnswer,
  OptionsStrategyPayload,
  OptionsStrategyRequest,
} from "@/lib/types";
import { ConfidenceBreakdown } from "./ConfidenceBreakdown";
import { InfoTooltip } from "./InfoTooltip";
import { ResultSummary } from "./ResultSummary";
import { TraceableMethodScorecard } from "./TraceableMethodScorecard";
import {
  IntermediatePnLChart,
  type IntermediateLeg,
} from "./IntermediatePnLChart";
import { PayoffChart, type PayoffLeg } from "./PayoffChart";
import { VerificationBadge } from "./VerificationBadge";
import { WhyPartialExpander } from "./WhyPartialExpander";

interface Props {
  answer: FinalAnswer;
  request?: OptionsStrategyRequest;
}

function isStrategyPayload(
  p: FinalAnswer["primary_result"],
): p is OptionsStrategyPayload {
  return p.kind === "options_strategy";
}

export function StrategyResultCard({ answer, request }: Props) {
  if (!isStrategyPayload(answer.primary_result)) {
    return (
      <div className="text-sm text-rose-700">
        Unexpected payload — expected options_strategy.
      </div>
    );
  }
  const primary = answer.primary_result;
  const cross = answer.verification.cross_method;
  const netPremium = primary.net_premium;
  const isDebit = netPremium > 0;
  const isCredit = netPremium < 0;

  // Build PayoffLeg[] from primary result so the chart uses the multi-leg path.
  const payoffLegs: PayoffLeg[] = primary.legs.map((leg) => ({
    strike: leg.strike,
    premium: leg.price,
    optionType: leg.option_type,
    quantity: leg.quantity,
  }));

  return (
    <div className="space-y-6">
      <ResultSummary answer={answer} />

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center text-xs uppercase tracking-wide text-zinc-500">
            <span>Net {isCredit ? "credit" : "premium"}</span>
            <InfoTooltip body={STRATEGY_OUTPUTS.netPremium.info} />
          </div>
          <div
            className={`mt-1 font-mono text-4xl font-semibold ${
              isCredit ? "text-emerald-700" : "text-zinc-900"
            }`}
          >
            {isCredit ? "−" : isDebit ? "" : ""}$
            {Math.abs(netPremium).toFixed(4)}
          </div>
          <div className="mt-0.5 text-xs text-zinc-500">
            {primary.legs.length} legs ·{" "}
            {isDebit
              ? "you pay this to open"
              : isCredit
                ? "you collect this when opening"
                : "even"}
          </div>
        </div>
        <VerificationBadge status={answer.verification_status} />
      </div>

      <p className="text-sm leading-relaxed text-zinc-700">
        {answer.explanation}
      </p>

      <WhyPartialExpander
        status={answer.verification_status}
        verification={answer.verification}
        calculatorResults={answer.calculator_results}
        family="options"
      />

      <ConfidenceBreakdown verification={answer.verification} />

      {request && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Aggregate payoff at expiry
          </div>
          <div className="mt-2">
            <PayoffChart spot={request.spot} legs={payoffLegs} />
          </div>
        </div>
      )}

      {request && (
        <div>
          <div className="flex items-center text-xs font-semibold uppercase tracking-wide text-zinc-500">
            <span>P/L over time</span>
            <InfoTooltip body="P/L estimated at four points between today and the longest leg's expiry, holding vol/rates constant. Useful for calendars and other time-sensitive structures where the at-expiry chart hides interim behaviour." />
          </div>
          <div className="mt-2">
            <IntermediatePnLChart
              spot={request.spot}
              riskFreeRate={request.risk_free_rate}
              dividendYield={request.dividend_yield ?? 0}
              legs={primary.legs.map(
                (l) =>
                  ({
                    strike: l.strike,
                    premium: l.price,
                    optionType: l.option_type,
                    quantity: l.quantity,
                    time_to_expiry_years: l.time_to_expiry_years,
                    volatility: l.volatility,
                  }) satisfies IntermediateLeg,
              )}
            />
          </div>
        </div>
      )}

      {/* Per-leg breakdown */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Per-leg breakdown
        </div>
        <div className="mt-2 overflow-hidden rounded-lg border border-zinc-200">
          <table className="w-full text-xs">
            <thead className="bg-zinc-50 text-zinc-600">
              <tr>
                <th className="px-3 py-1.5 text-left font-medium">#</th>
                <th className="px-3 py-1.5 text-left font-medium">Side</th>
                <th className="px-3 py-1.5 text-left font-medium">Type</th>
                <th className="px-3 py-1.5 text-right font-medium">Strike</th>
                <th className="px-3 py-1.5 text-right font-medium">Days</th>
                <th className="px-3 py-1.5 text-right font-medium">IV</th>
                <th className="px-3 py-1.5 text-right font-medium">Qty</th>
                <th className="px-3 py-1.5 text-right font-medium">Price</th>
                <th className="px-3 py-1.5 text-right font-medium">Δ leg</th>
              </tr>
            </thead>
            <tbody>
              {primary.legs.map((leg, i) => {
                const long = leg.quantity > 0;
                const legCashflow = leg.quantity * leg.price;
                return (
                  <tr
                    key={i}
                    className="border-t border-zinc-200 font-mono text-zinc-800"
                  >
                    <td className="px-3 py-1.5 text-zinc-500">{i + 1}</td>
                    <td
                      className={`px-3 py-1.5 ${
                        long ? "text-emerald-700" : "text-rose-700"
                      }`}
                    >
                      {long ? "long" : "short"}
                    </td>
                    <td className="px-3 py-1.5 capitalize">
                      {leg.option_type}
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      ${leg.strike.toFixed(2)}
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      {Math.round(leg.time_to_expiry_years * 365)}d
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      {(leg.volatility * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      {leg.quantity > 0 ? "+" : ""}
                      {leg.quantity}
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      ${leg.price.toFixed(4)}
                    </td>
                    <td
                      className={`px-3 py-1.5 text-right ${
                        legCashflow >= 0 ? "text-zinc-900" : "text-emerald-700"
                      }`}
                    >
                      {legCashflow >= 0 ? "+" : "−"}$
                      {Math.abs(legCashflow).toFixed(4)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-zinc-50">
              <tr>
                <td
                  colSpan={8}
                  className="px-3 py-1.5 text-right font-semibold text-zinc-700"
                >
                  Net premium
                </td>
                <td
                  className={`px-3 py-1.5 text-right font-mono font-semibold ${
                    isCredit ? "text-emerald-700" : "text-zinc-900"
                  }`}
                >
                  {isCredit ? "−" : ""}${Math.abs(netPremium).toFixed(4)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Net Greeks */}
      <div>
        <div className="flex items-center text-xs font-semibold uppercase tracking-wide text-zinc-500">
          <span>Net Greeks</span>
          <InfoTooltip body={STRATEGY_OUTPUTS.netGreeks.info} />
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-5">
          <Stat
            label={GREEKS.delta.label}
            info={GREEKS.delta.info}
            value={primary.net_greeks.delta}
            digits={4}
          />
          <Stat
            label={GREEKS.gamma.label}
            info={GREEKS.gamma.info}
            value={primary.net_greeks.gamma}
            digits={5}
          />
          <Stat
            label={GREEKS.vega.label}
            info={GREEKS.vega.info}
            value={primary.net_greeks.vega}
            digits={4}
          />
          <Stat
            label={GREEKS.theta.label}
            info={GREEKS.theta.info}
            value={primary.net_greeks.theta}
            digits={4}
          />
          <Stat
            label={GREEKS.rho.label}
            info={GREEKS.rho.info}
            value={primary.net_greeks.rho}
            digits={4}
          />
        </div>
      </div>

      {/* Per-method scorecard (with leg-level cross-check summary) */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Per-method scorecard
        </div>
        {cross ? (
          <div className="mt-1 text-[11px] text-zinc-500">
            Worst-leg max Δ abs {cross.max_absolute_delta.toExponential(2)} ·
            max Δ rel {cross.max_relative_delta.toExponential(2)} ·{" "}
            <span
              className={
                cross.passed
                  ? "font-semibold text-emerald-700"
                  : "font-semibold text-rose-700"
              }
            >
              {cross.passed ? "all legs within tolerance" : "LEG DISAGREEMENT"}
            </span>
          </div>
        ) : (
          <div className="mt-1 text-[11px] text-zinc-500">
            Only one method available — cross-check skipped.
          </div>
        )}
        <div className="mt-2">
          <TraceableMethodScorecard
            answer={answer}
            valueFormatter={(v) => `$${v.toFixed(4)} net`}
          />
        </div>
      </div>

      {/* Invariants — list per-leg failures explicitly */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Invariants (per leg)
        </div>
        <div className="mt-2 space-y-1">
          {answer.verification.invariants.map((inv) => (
            <div
              key={inv.name}
              className="flex items-center gap-2 text-xs text-zinc-600"
            >
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${
                  inv.passed ? "bg-emerald-500" : "bg-rose-500"
                }`}
              />
              <span className="font-mono">{inv.name}</span>
              {!inv.passed && inv.detail && (
                <span className="ml-2 text-rose-700">{inv.detail}</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {answer.limitations.length > 0 && (
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
          <div className="font-semibold text-zinc-700">Limitations</div>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {answer.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  digits,
  info,
}: {
  label: string;
  value: number;
  digits: number;
  info?: string;
}) {
  return (
    <div className="rounded-md border border-zinc-200 px-2 py-1.5">
      <div className="flex items-center text-[10px] text-zinc-500">
        <span>{label}</span>
        {info && <InfoTooltip body={info} />}
      </div>
      <div className="font-mono text-xs text-zinc-900">
        {value.toFixed(digits)}
      </div>
    </div>
  );
}
