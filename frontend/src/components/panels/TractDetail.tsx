"use client";

import type { TractProperties } from "@/lib/types";
import { getDisplayName } from "@/lib/constants";

interface TractDetailProps {
  tract: TractProperties | null;
}

function classificationColor(c: string): string {
  switch (c) {
    case "low":
      return "bg-green-600";
    case "moderate":
      return "bg-yellow-500";
    case "high":
      return "bg-orange-500";
    case "critical":
      return "bg-red-600";
    default:
      return "bg-gray-600";
  }
}

function scoreBadge(score: number, kind: "drs" | "ebs") {
  let color: string;
  if (kind === "drs") {
    if (score < 25) color = "bg-green-600/20 text-green-400 border-green-700/50";
    else if (score < 50) color = "bg-yellow-600/20 text-yellow-400 border-yellow-700/50";
    else if (score < 75) color = "bg-orange-600/20 text-orange-400 border-orange-700/50";
    else color = "bg-red-600/20 text-red-400 border-red-700/50";
  } else {
    if (score < 25) color = "bg-red-600/20 text-red-400 border-red-700/50";
    else if (score < 50) color = "bg-orange-600/20 text-orange-400 border-orange-700/50";
    else if (score < 75) color = "bg-yellow-600/20 text-yellow-400 border-yellow-700/50";
    else color = "bg-green-600/20 text-green-400 border-green-700/50";
  }
  return (
    <span className={`${color} text-sm font-bold px-3 py-1 rounded-lg border`}>
      {score.toFixed(1)}
    </span>
  );
}

function fmtPct(v: number | null): string {
  if (v == null) return "N/A";
  if (v >= 0 && v <= 1) return `${(v * 100).toFixed(1)}%`;
  return `${v.toFixed(1)}%`;
}

function fmtDollar(v: number | null): string {
  if (v == null) return "N/A";
  return `$${v.toLocaleString()}`;
}

function fmtNum(v: number | null): string {
  if (v == null) return "N/A";
  return v.toLocaleString();
}

export default function TractDetail({ tract }: TractDetailProps) {
  if (!tract) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-500">
        <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-8 h-8 text-gray-600">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-400">No tract selected</p>
        <p className="text-xs text-gray-600 mt-1">
          Click a census tract on the map to view details
        </p>
      </div>
    );
  }

  const displayName = getDisplayName(tract.county_name, tract.geoid);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="pb-4 border-b border-gray-800">
        <h3 className="text-xl font-bold text-white leading-tight">
          {displayName}
        </h3>
        <p className="text-xs text-gray-500 font-mono mt-1">
          GEOID {tract.geoid}
        </p>
      </div>

      {/* Scores */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
          <div className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wider">
            Displacement Risk
          </div>
          <div className="flex items-center gap-2">
            {scoreBadge(tract.drs_composite, "drs")}
            <span
              className={`text-[10px] uppercase font-semibold tracking-wide px-2 py-0.5 rounded-md ${classificationColor(
                tract.drs_classification
              )} text-white`}
            >
              {tract.drs_classification}
            </span>
          </div>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
          <div className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wider">
            Env. Benefit
          </div>
          {scoreBadge(tract.ebs_composite, "ebs")}
        </div>
      </div>

      {/* Key Stats */}
      <div>
        <div className="text-xs text-gray-400 mb-3 font-medium uppercase tracking-wider">
          Key Stats
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl divide-y divide-gray-700/50">
          {[
            ["Population", fmtNum(tract.total_population)],
            ["Median Rent", fmtDollar(tract.median_rent)],
            ["Renters", fmtPct(tract.pct_renters)],
            ["Rent Burdened", fmtPct(tract.pct_rent_burdened)],
            ["Non-White", fmtPct(tract.pct_nonwhite)],
          ].map(([label, value]) => (
            <div
              key={label}
              className="flex items-center justify-between px-4 py-2.5"
            >
              <span className="text-sm text-gray-400">{label}</span>
              <span className="text-sm font-medium text-gray-200">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
