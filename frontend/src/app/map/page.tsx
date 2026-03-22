"use client";

import { useCallback, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import type {
  TractProperties,
  Intervention,
  InterventionType,
  SimulationResult,
} from "@/lib/types";
import { simulateScenario, optimizeScenario } from "@/lib/scoring-client";
import { INTERVENTION_TYPES } from "@/lib/constants";
import InterventionBuilder from "@/components/panels/InterventionBuilder";
import TractDetail from "@/components/panels/TractDetail";
import DecisionPanel from "@/components/panels/DecisionPanel";
import Legend from "@/components/map/Legend";

// Dynamic import for the map to avoid SSR issues with maplibre-gl
const TractMap = dynamic(() => import("@/components/map/TractMap"), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center bg-gray-950 text-gray-500">
      <div className="flex flex-col items-center gap-3">
        <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
        <span className="text-sm">Loading map...</span>
      </div>
    </div>
  ),
});

export default function MapPage() {
  // Core state
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [policies, setPolicies] = useState<string[]>([]);
  const [selectedTract, setSelectedTract] = useState<TractProperties | null>(null);

  // Simulation state
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [optimizeSummary, setOptimizeSummary] = useState<string | null>(null);
  const [optimizeLocations, setOptimizeLocations] = useState<
    Array<{
      lat: number;
      lng: number;
      geoid: string;
      county_name: string;
      reasoning: string;
      optimization_score: number;
    }>
  | null>(null);

  // UI state
  const [metric, setMetric] = useState<"drs" | "ebs">("drs");
  const [placingIntervention, setPlacingIntervention] = useState(false);
  const [pendingType, setPendingType] = useState<InterventionType>("park");
  const [pendingScale, setPendingScale] = useState(10);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Map bounds stored via ref to avoid re-renders
  const mapBoundsRef = useRef<{
    min_lat: number;
    min_lng: number;
    max_lat: number;
    max_lng: number;
  } | null>(null);

  // Handlers
  const handleStartPlacing = useCallback(
    (type: InterventionType, scale: number) => {
      setPendingType(type);
      setPendingScale(scale);
      setPlacingIntervention(true);
    },
    []
  );

  const handleMapClick = useCallback(
    (lat: number, lng: number) => {
      if (placingIntervention) {
        const typeInfo = INTERVENTION_TYPES.find((t) => t.value === pendingType);
        const newIntervention: Intervention = {
          id: crypto.randomUUID(),
          type: pendingType,
          location: { lat, lng },
          scale_value: pendingScale,
          scale_unit: typeInfo?.unit ?? "units",
        };
        setInterventions((prev) => [...prev, newIntervention]);
        setPlacingIntervention(false);
      }
    },
    [placingIntervention, pendingType, pendingScale]
  );

  const handleTractClick = useCallback(
    (tract: TractProperties) => {
      if (!placingIntervention) {
        setSelectedTract(tract);
      }
    },
    [placingIntervention]
  );

  const handleRemoveIntervention = useCallback((id: string) => {
    setInterventions((prev) => prev.filter((i) => i.id !== id));
  }, []);

  const handleTogglePolicy = useCallback((policy: string) => {
    setPolicies((prev) =>
      prev.includes(policy)
        ? prev.filter((p) => p !== policy)
        : [...prev, policy]
    );
  }, []);

  const handleBoundsChange = useCallback(
    (bounds: {
      min_lat: number;
      min_lng: number;
      max_lat: number;
      max_lng: number;
    }) => {
      mapBoundsRef.current = bounds;
    },
    []
  );

  const handleSimulate = useCallback(async () => {
    if (interventions.length === 0) return;
    setIsSimulating(true);
    setError(null);
    setOptimizeSummary(null);
    setOptimizeLocations(null);

    try {
      const interventionPayload = interventions.map((i) => ({
        type: i.type,
        lat: i.location.lat,
        lng: i.location.lng,
        scale_value: i.scale_value,
        scale_unit: i.scale_unit,
      }));

      if (policies.length === 0) {
        // No policies — single simulation
        const result = await simulateScenario({
          interventions: interventionPayload,
        });
        setSimulationResult(result);
      } else {
        // Two-pass: first simulate to get affected tracts, then re-simulate with mitigations
        const firstPass = await simulateScenario({
          interventions: interventionPayload,
        });

        // Get all affected tract GEOIDs as mitigation targets
        const affectedGeoids = firstPass.affected_tracts.map(
          (t: { geoid: string }) => t.geoid
        );

        // Re-simulate with policies applied to all affected tracts
        const result = await simulateScenario({
          interventions: interventionPayload,
          mitigations: policies.map((p) => ({
            type: p,
            target_geoids: affectedGeoids,
          })),
        });
        setSimulationResult(result);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      if (msg.includes("fetch") || msg.includes("ECONNREFUSED")) {
        setError(
          "Scoring service unavailable. Make sure it is running at localhost:8000."
        );
      } else {
        setError(msg);
      }
    } finally {
      setIsSimulating(false);
    }
  }, [interventions, policies]);

  const handleOptimize = useCallback(async () => {
    setIsOptimizing(true);
    setError(null);
    setOptimizeSummary(null);
    setOptimizeLocations(null);

    try {
      const bounds = mapBoundsRef.current;
      if (!bounds) {
        throw new Error("Map not ready");
      }

      const typeInfo = INTERVENTION_TYPES.find((t) => t.value === pendingType);
      const payload = {
        type: pendingType,
        scale_value: pendingScale,
        scale_unit: typeInfo?.unit ?? "units",
        ...bounds,
      };

      const result = await optimizeScenario(payload);

      // Place optimal locations as interventions
      if (result.optimal_locations && Array.isArray(result.optimal_locations)) {
        const newInterventions: Intervention[] = result.optimal_locations.map(
          (loc: {
            lat: number;
            lng: number;
            type?: string;
            scale_value?: number;
            scale_unit?: string;
            geoid?: string;
            county_name?: string;
            reasoning?: string;
            optimization_score?: number;
          }) => ({
            id: crypto.randomUUID(),
            type: (loc.type || pendingType) as InterventionType,
            location: { lat: loc.lat, lng: loc.lng },
            scale_value: loc.scale_value || pendingScale,
            scale_unit: loc.scale_unit || typeInfo?.unit || "units",
          })
        );
        setInterventions((prev) => [...prev, ...newInterventions]);
        setOptimizeLocations(
          result.optimal_locations.map(
            (loc: {
              lat: number;
              lng: number;
              geoid?: string;
              county_name?: string;
              reasoning?: string;
              optimization_score?: number;
            }) => ({
              lat: loc.lat,
              lng: loc.lng,
              geoid: loc.geoid || "",
              county_name: loc.county_name || "",
              reasoning: loc.reasoning || "",
              optimization_score: loc.optimization_score || 0,
            })
          )
        );
      }

      if (result.summary) {
        setOptimizeSummary(result.summary);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setError(msg);
    } finally {
      setIsOptimizing(false);
    }
  }, [pendingType, pendingScale]);

  // Build predicted scores map from simulation result
  const predictedScores =
    simulationResult?.affected_tracts.reduce(
      (acc, tr) => {
        acc[tr.geoid] = tr.predicted_drs;
        return acc;
      },
      {} as Record<string, number>
    ) ?? undefined;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-950">
      {/* Left Sidebar */}
      <aside className="w-80 bg-gray-900/80 backdrop-blur border-r border-gray-800/50 flex-shrink-0 overflow-y-auto flex flex-col">
        {/* App header */}
        <div className="px-4 py-3 border-b border-gray-800/50 flex items-center gap-2.5">
          <Link
            href="/"
            className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
          >
            <div className="w-7 h-7 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold text-xs">
              GW
            </div>
            <span className="text-sm font-semibold tracking-tight">
              GreenWatch
            </span>
          </Link>
        </div>

        <div className="p-4 flex-1">
          <InterventionBuilder
            interventions={interventions}
            onRemoveIntervention={handleRemoveIntervention}
            placingIntervention={placingIntervention}
            onStartPlacing={handleStartPlacing}
            onSimulate={handleSimulate}
            onOptimize={handleOptimize}
            isSimulating={isSimulating}
            isOptimizing={isOptimizing}
            policies={policies}
            onTogglePolicy={handleTogglePolicy}
            error={error}
          />
        </div>
      </aside>

      {/* Center - Map */}
      <div className="flex-1 relative bg-gray-950">
        {/* Metric switcher */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex gap-1 bg-gray-900/90 backdrop-blur-md rounded-xl p-1 border border-gray-700/50 shadow-lg">
          <button
            onClick={() => setMetric("drs")}
            className={`px-4 py-2 text-xs font-medium rounded-lg transition-all ${
              metric === "drs"
                ? "bg-emerald-600 text-white shadow-sm"
                : "text-gray-400 hover:text-white hover:bg-gray-800/50"
            }`}
          >
            Displacement Risk
          </button>
          <button
            onClick={() => setMetric("ebs")}
            className={`px-4 py-2 text-xs font-medium rounded-lg transition-all ${
              metric === "ebs"
                ? "bg-emerald-600 text-white shadow-sm"
                : "text-gray-400 hover:text-white hover:bg-gray-800/50"
            }`}
          >
            Environmental Benefit
          </button>
        </div>

        <TractMap
          tracts={null}
          selectedTract={selectedTract}
          onTractClick={handleTractClick}
          onMapClick={handleMapClick}
          metric={metric}
          interventions={interventions}
          predictedScores={predictedScores}
          showPredicted={false}
          placing={placingIntervention}
          onBoundsChange={handleBoundsChange}
        />

        <Legend metric={metric} />

        {placingIntervention && (
          <div className="absolute top-4 right-4 z-10 bg-emerald-950/90 backdrop-blur-md text-emerald-300 text-sm px-5 py-3 rounded-xl border border-emerald-700/50 shadow-lg flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Click map to place intervention
          </div>
        )}
      </div>

      {/* Right Sidebar */}
      <aside className="w-96 bg-gray-900/80 backdrop-blur border-l border-gray-800/50 flex-shrink-0 overflow-y-auto">
        <div className="p-5">
          {simulationResult ? (
            <div>
              <div className="flex items-center justify-between mb-5 pb-4 border-b border-gray-800">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-700/50 flex items-center justify-center">
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
                        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
                      />
                    </svg>
                  </div>
                  <h2 className="text-base font-semibold">Decision Report</h2>
                </div>
                <button
                  onClick={() => {
                    setSimulationResult(null);
                    setOptimizeSummary(null);
                    setOptimizeLocations(null);
                  }}
                  className="text-xs text-gray-500 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded-lg transition-colors"
                >
                  Clear
                </button>
              </div>
              <DecisionPanel
                result={simulationResult}
                optimizeSummary={optimizeSummary}
                optimizeLocations={optimizeLocations}
              />
            </div>
          ) : selectedTract ? (
            <div>
              <div className="flex items-center gap-2 mb-5 pb-4 border-b border-gray-800">
                <div className="w-7 h-7 rounded-lg bg-gray-800 flex items-center justify-center">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="w-4 h-4 text-gray-400"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"
                    />
                  </svg>
                </div>
                <h2 className="text-base font-semibold">Tract Details</h2>
              </div>
              <TractDetail tract={selectedTract} />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center mb-4">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  className="w-8 h-8 text-gray-600"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"
                  />
                </svg>
              </div>
              <p className="text-sm font-medium text-gray-400 text-center">
                Click a census tract or place an intervention to begin
              </p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
