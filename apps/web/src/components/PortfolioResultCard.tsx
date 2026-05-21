import { PORTFOLIO_OUTPUTS } from "@/lib/copy";
import type { FinalAnswer, PortfolioPayload } from "@/lib/types";
import { ConfidenceBreakdown } from "./ConfidenceBreakdown";
import { InfoTooltip } from "./InfoTooltip";
import { VerificationBadge } from "./VerificationBadge";
import { WeightsChart } from "./WeightsChart";
import { WhyPartialExpander } from "./WhyPartialExpander";

interface Props {
  answer: FinalAnswer;
}

function isPortfolioPayload(
  p: FinalAnswer["primary_result"],
): p is PortfolioPayload {
  return p.kind === "portfolio";
}

const FMT_PCT = (v: number, digits: number = 2) =>
  `${(v * 100).toFixed(digits)}%`;

export function PortfolioResultCard({ answer }: Props) {
  if (!isPortfolioPayload(answer.primary_result)) {
    return (
      <div className="text-sm text-rose-700">
        Unexpected payload — expected portfolio.
      </div>
    );
  }
  const primary = answer.primary_result;
  const stability =
    primary.instability_score !== null ? 1 - primary.instability_score : null;
  const objLabel =
    primary.objective === "mean_variance" ? "Mean-variance" : "Max-Sharpe";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-zinc-500">
            {objLabel} portfolio
          </div>
          <div className="mt-1 flex items-baseline gap-3">
            <div>
              <div className="text-[10px] text-zinc-500">Sharpe</div>
              <div className="font-mono text-2xl font-semibold text-zinc-900">
                {primary.sharpe_ratio.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-zinc-500">E[r]</div>
              <div className="font-mono text-2xl font-semibold text-emerald-700">
                {FMT_PCT(primary.expected_return_annualised)}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-zinc-500">σ</div>
              <div className="font-mono text-2xl font-semibold text-zinc-900">
                {FMT_PCT(primary.volatility_annualised)}
              </div>
            </div>
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
        family="var"
      />

      <ConfidenceBreakdown verification={answer.verification} />

      <div>
        <div className="flex items-center text-xs font-semibold uppercase tracking-wide text-zinc-500">
          <span>Weights vs risk contribution</span>
          <InfoTooltip body={PORTFOLIO_OUTPUTS.riskContribution.info} />
        </div>
        <div className="mt-2">
          <WeightsChart weights={primary.weights} />
        </div>
      </div>

      {stability !== null && (
        <div>
          <div className="flex items-center text-xs font-semibold uppercase tracking-wide text-zinc-500">
            <span>Solution stability</span>
            <InfoTooltip body={PORTFOLIO_OUTPUTS.instability.info} />
          </div>
          <div className="mt-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-600">
                Weights move under ±1% input perturbation
              </span>
              <span
                className={
                  stability >= 0.75
                    ? "font-mono font-semibold text-emerald-700"
                    : stability >= 0.4
                      ? "font-mono font-semibold text-amber-700"
                      : "font-mono font-semibold text-rose-700"
                }
              >
                {(stability * 100).toFixed(0)}% stable
              </span>
            </div>
            <p className="mt-1 text-zinc-600">
              {stability >= 0.75
                ? "The optimal weights barely move when expected returns wiggle — trust the allocation as a number."
                : stability >= 0.4
                  ? "The solution shifts noticeably under small input perturbations. Treat the weights as a direction, not a precise allocation."
                  : "Highly unstable — small changes in inputs flip large fractions of the portfolio. Don't trust the exact weights; use as a rough qualitative steer."}
            </p>
          </div>
        </div>
      )}

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Solver
        </div>
        <div className="mt-2 rounded-md border border-zinc-200 px-3 py-2 text-xs text-zinc-700">
          <span className="font-mono">{primary.solver_name}</span>
          {primary.iterations !== null && (
            <span className="ml-2 text-zinc-500">
              · {primary.iterations} iterations
            </span>
          )}
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
