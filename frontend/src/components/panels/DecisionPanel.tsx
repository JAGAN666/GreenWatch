"use client";

import type { SimulationResult } from "@/lib/types";
import { getDisplayName } from "@/lib/constants";


interface OptimizeLocation {
  lat: number;
  lng: number;
  geoid: string;
  county_name: string;
  reasoning: string;
  optimization_score: number;
}

interface DecisionPanelProps {
  result: SimulationResult;
  optimizeSummary: string | null;
  optimizeLocations: OptimizeLocation[] | null;
}

function deltaColor(delta: number): string {
  if (delta > 5) return "text-red-400";
  if (delta > 0) return "text-orange-400";
  if (delta < -5) return "text-green-400";
  if (delta < 0) return "text-emerald-400";
  return "text-gray-400";
}

export default function DecisionPanel({
  result,
  optimizeSummary,
  optimizeLocations,
}: DecisionPanelProps) {
  const sorted = [...result.affected_tracts].sort(
    (a, b) => b.delta_drs - a.delta_drs
  );
  const top5 = sorted.slice(0, 5);

  // Compute aggregated metrics
  const avgCurrentDrs =
    sorted.length > 0
      ? sorted.reduce((sum, t) => sum + t.current_drs, 0) / sorted.length
      : 0;
  const avgPredictedDrs =
    sorted.length > 0
      ? sorted.reduce((sum, t) => sum + t.predicted_drs, 0) / sorted.length
      : 0;
  const avgCurrentEbs =
    sorted.length > 0
      ? sorted.reduce((sum, t) => sum + t.current_ebs, 0) / sorted.length
      : 0;
  const avgPredictedEbs =
    sorted.length > 0
      ? sorted.reduce((sum, t) => sum + t.predicted_ebs, 0) / sorted.length
      : 0;

  const drsChange = avgPredictedDrs - avgCurrentDrs;
  const ebsChange = avgPredictedEbs - avgCurrentEbs;

  const warningTracts = sorted.filter((t) => t.equity_warning);
  const warningPop =
    warningTracts.length > 0 && sorted.length > 0
      ? Math.round(
          result.total_population_affected *
            (warningTracts.length / sorted.length)
        )
      : 0;

  // Generate AI insight from highest-DRS affected tract
  const highestRiskTract = sorted[0];
  let aiInsight = "";
  if (result.summary_text) {
    aiInsight = result.summary_text;
  } else if (highestRiskTract) {
    aiInsight = `The most affected tract (${highestRiskTract.geoid}) sees a displacement risk increase of ${highestRiskTract.delta_drs.toFixed(1)} points. ${
      result.equity_warnings_count > 0
        ? `${result.equity_warnings_count} tracts with vulnerable communities require protective policies.`
        : "No critical equity warnings were triggered."
    }`;
  }

  return (
    <div className="space-y-5">
      {/* 1. HEADLINE METRIC */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
        <div className="text-4xl font-bold text-white leading-tight">
          {result.total_population_affected.toLocaleString()}
        </div>
        <div className="text-sm text-gray-400 mt-1">
          {optimizeSummary
            ? "residents in the optimized plan area"
            : "residents face displacement risk from this plan"}
        </div>
      </div>

      {/* 2. EQUITY ALERT */}
      {result.equity_warnings_count > 0 && (
        <div className="bg-red-950/60 border border-red-700/50 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-red-900/60 flex items-center justify-center shrink-0 mt-0.5">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="w-5 h-5 text-red-400"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-red-300">
                {result.equity_warnings_count} tract
                {result.equity_warnings_count > 1 ? "s" : ""} with vulnerable
                communities at significant risk
              </p>
              <p className="text-xs text-red-400/70 mt-1">
                Approximately {warningPop.toLocaleString()} residents in
                high-risk areas need protective policies
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 3. AI INSIGHT */}
      {aiInsight && (
        <div className="bg-blue-950/40 border border-blue-700/40 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="w-4 h-4 text-blue-400"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
              />
            </svg>
            <span className="text-xs font-semibold text-blue-300 uppercase tracking-wider">
              AI Insight
            </span>
          </div>
          <p className="text-sm text-blue-200/80 leading-relaxed">{aiInsight}</p>
        </div>
      )}

      {/* 4. BEFORE vs AFTER */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
        <div className="text-xs text-gray-400 font-medium uppercase tracking-wider mb-3">
          Before vs After
        </div>
        <div className="grid grid-cols-2 gap-4">
          {/* Before column */}
          <div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-medium">
              Before
            </div>
            <div className="space-y-2">
              <div>
                <div className="text-xs text-gray-500">Avg DRS</div>
                <div className="text-lg font-bold text-gray-300">
                  {avgCurrentDrs.toFixed(1)}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Avg EBS</div>
                <div className="text-lg font-bold text-gray-300">
                  {avgCurrentEbs.toFixed(1)}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Warnings</div>
                <div className="text-lg font-bold text-gray-300">0</div>
              </div>
            </div>
          </div>
          {/* After column */}
          <div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-medium">
              After
            </div>
            <div className="space-y-2">
              <div>
                <div className="text-xs text-gray-500">Avg DRS</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-lg font-bold text-gray-200">
                    {avgPredictedDrs.toFixed(1)}
                  </span>
                  <span
                    className={`text-xs font-semibold ${deltaColor(drsChange)}`}
                  >
                    {drsChange > 0 ? "+" : ""}
                    {drsChange.toFixed(1)}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Avg EBS</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-lg font-bold text-gray-200">
                    {avgPredictedEbs.toFixed(1)}
                  </span>
                  <span
                    className={`text-xs font-semibold ${
                      ebsChange > 0 ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    {ebsChange > 0 ? "+" : ""}
                    {ebsChange.toFixed(1)}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Warnings</div>
                <div
                  className={`text-lg font-bold ${
                    result.equity_warnings_count > 0
                      ? "text-red-400"
                      : "text-green-400"
                  }`}
                >
                  {result.equity_warnings_count}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 5. AI RECOMMENDATION (if optimize was used) */}
      {optimizeSummary && (
        <div className="bg-emerald-950/40 border border-emerald-700/40 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="w-4 h-4 text-emerald-400"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
              />
            </svg>
            <span className="text-xs font-semibold text-emerald-300 uppercase tracking-wider">
              AI Recommendation
            </span>
          </div>
          <p className="text-sm text-emerald-200/80 leading-relaxed">
            {optimizeSummary}
          </p>
          {optimizeLocations && optimizeLocations.length > 0 && (
            <div className="mt-3 space-y-2">
              {optimizeLocations.slice(0, 3).map((loc, i) => (
                <div
                  key={i}
                  className="bg-emerald-900/20 rounded-lg p-2 text-xs"
                >
                  <div className="font-medium text-emerald-200">
                    {loc.county_name || `Location ${i + 1}`}
                  </div>
                  {loc.reasoning && (
                    <div className="text-emerald-300/60 mt-0.5">
                      {loc.reasoning}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 6. TOP AFFECTED AREAS */}
      {top5.length > 0 && (
        <div>
          <div className="text-xs text-gray-400 font-medium uppercase tracking-wider mb-3">
            Top Affected Areas
          </div>
          <div className="space-y-2">
            {top5.map((tr) => (
              <div
                key={tr.geoid}
                className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 flex items-center justify-between"
              >
                <div>
                  <div className="text-sm font-medium text-gray-200">
                    {getDisplayName((tr as Record<string, unknown>).county_name as string || "", tr.geoid)}
                  </div>
                  <div className="text-xs text-gray-500">
                    DRS: {tr.current_drs.toFixed(1)} &rarr;{" "}
                    {tr.predicted_drs.toFixed(1)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm font-bold ${deltaColor(tr.delta_drs)}`}
                  >
                    {tr.delta_drs > 0 ? "+" : ""}
                    {tr.delta_drs.toFixed(1)}
                  </span>
                  {tr.equity_warning && (
                    <span className="bg-red-900/40 text-red-400 text-[10px] font-semibold px-2 py-0.5 rounded-md border border-red-700/40">
                      HIGH RISK
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
