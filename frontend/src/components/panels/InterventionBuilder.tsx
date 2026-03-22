"use client";

import { useState } from "react";
import type { Intervention, InterventionType } from "@/lib/types";
import { INTERVENTION_TYPES, POLICY_OPTIONS, getDisplayName } from "@/lib/constants";

interface InterventionBuilderProps {
  interventions: Intervention[];
  onRemoveIntervention: (id: string) => void;
  placingIntervention: boolean;
  onStartPlacing: (type: InterventionType, scale: number) => void;
  onSimulate: () => void;
  onOptimize: () => void;
  isSimulating: boolean;
  isOptimizing: boolean;
  policies: string[];
  onTogglePolicy: (policy: string) => void;
  error: string | null;
}

export default function InterventionBuilder({
  interventions,
  onRemoveIntervention,
  placingIntervention,
  onStartPlacing,
  onSimulate,
  onOptimize,
  isSimulating,
  isOptimizing,
  policies,
  onTogglePolicy,
  error,
}: InterventionBuilderProps) {
  const [type, setType] = useState<InterventionType>("park");
  const [scale, setScale] = useState(10);

  const selectedType = INTERVENTION_TYPES.find((t) => t.value === type)!;

  function handlePlace() {
    onStartPlacing(type, scale);
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-gray-100">What do you want to build?</h2>
      </div>

      {/* Type dropdown */}
      <div>
        <label className="text-xs text-gray-400 block mb-1.5 font-medium uppercase tracking-wider">
          Type
        </label>
        <select
          value={type}
          onChange={(e) => setType(e.target.value as InterventionType)}
          className="w-full bg-gray-900 text-sm rounded-lg px-3 py-2 border border-gray-700 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500/30 transition-colors"
        >
          {INTERVENTION_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {/* Scale input */}
      <div>
        <label className="text-xs text-gray-400 block mb-1.5 font-medium uppercase tracking-wider">
          Scale ({selectedType.unit})
        </label>
        <input
          type="range"
          min={1}
          max={100}
          value={scale}
          onChange={(e) => setScale(Number(e.target.value))}
          className="w-full accent-emerald-500"
        />
        <div className="flex justify-between mt-1">
          <span className="text-xs text-gray-500">1</span>
          <span className="text-sm font-medium text-gray-300">
            {scale} {selectedType.unit}
          </span>
          <span className="text-xs text-gray-500">100</span>
        </div>
      </div>

      {/* Place button */}
      {placingIntervention ? (
        <div className="bg-emerald-950/50 border border-emerald-700/50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <p className="text-emerald-300 text-sm font-semibold">Placement Mode</p>
          </div>
          <p className="text-emerald-400/70 text-xs mt-1">
            Click the map to place: {selectedType.label} ({scale} {selectedType.unit})
          </p>
        </div>
      ) : (
        <button
          onClick={handlePlace}
          className="w-full bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
          </svg>
          Click Map to Place
        </button>
      )}

      {/* Divider */}
      {interventions.length > 0 && (
        <>
          <div className="border-t border-gray-800" />

          {/* Placed Interventions */}
          <div>
            <h3 className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-3">
              Placed Interventions ({interventions.length})
            </h3>
            <div className="space-y-2">
              {interventions.map((inv) => {
                const typeInfo = INTERVENTION_TYPES.find((t) => t.value === inv.type);
                const locationName = getDisplayName("", "");
                return (
                  <div
                    key={inv.id}
                    className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 flex items-center justify-between group hover:border-gray-600 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: (typeInfo?.color || "#22c55e") + "20", border: `1px solid ${(typeInfo?.color || "#22c55e")}40` }}
                      >
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: typeInfo?.color || "#22c55e" }}
                        />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-200">
                          {typeInfo?.label ?? inv.type}
                        </div>
                        <div className="text-xs text-gray-500">
                          {inv.scale_value} {inv.scale_unit} &middot;{" "}
                          {inv.location.lat.toFixed(3)}, {inv.location.lng.toFixed(3)}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => onRemoveIntervention(inv.id)}
                      className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all p-1"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Divider */}
      <div className="border-t border-gray-800" />

      {/* Policy Protections */}
      <div>
        <h3 className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-3">
          Policy Protections
        </h3>
        <div className="space-y-2">
          {POLICY_OPTIONS.map((policy) => (
            <label
              key={policy.value}
              className="flex items-start gap-3 cursor-pointer bg-gray-800/30 hover:bg-gray-800/50 rounded-xl p-3 transition-colors"
            >
              <input
                type="checkbox"
                checked={policies.includes(policy.value)}
                onChange={() => onTogglePolicy(policy.value)}
                className="mt-0.5 rounded border-gray-600 text-emerald-500 focus:ring-emerald-500/30"
              />
              <div>
                <div className="text-sm font-medium text-gray-200">{policy.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{policy.description}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-gray-800" />

      {/* Action buttons */}
      <div className="space-y-2">
        <button
          onClick={onSimulate}
          disabled={interventions.length === 0 || isSimulating}
          className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-800 disabled:text-gray-600 disabled:border-gray-700 text-white text-sm font-semibold py-3 rounded-xl transition-colors border border-emerald-500 disabled:border-gray-700"
        >
          {isSimulating ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
              Simulating...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              Run Simulation
            </span>
          )}
        </button>

        <button
          onClick={onOptimize}
          disabled={isOptimizing}
          className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-600 disabled:border-gray-700 text-white text-sm font-semibold py-3 rounded-xl transition-colors border border-blue-500 disabled:border-gray-700"
        >
          {isOptimizing ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
              Optimizing...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
              </svg>
              AI Optimize
            </span>
          )}
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-950/50 border border-red-700/50 rounded-xl p-3 text-sm text-red-300">
          {error}
        </div>
      )}
    </div>
  );
}
