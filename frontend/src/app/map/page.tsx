"use client";

export default function MapPage() {
  return (
    <div className="flex h-screen w-screen">
      {/* Left Panel — Intervention Builder (placeholder) */}
      <aside className="w-80 bg-gray-900 border-r border-gray-800 p-4 flex-shrink-0 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Interventions</h2>
        <p className="text-sm text-gray-400">
          Simulation workbench will be built here — intervention builder,
          mitigation controls, scenario management.
        </p>
      </aside>

      {/* Center — Map */}
      <div className="flex-1 relative bg-gray-950">
        <div className="absolute inset-0 flex items-center justify-center text-gray-500">
          Deck.gl + Mapbox map will render here
        </div>
      </div>

      {/* Right Panel — Impact Analysis (placeholder) */}
      <aside className="w-96 bg-gray-900 border-l border-gray-800 p-4 flex-shrink-0 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Impact Analysis</h2>
        <p className="text-sm text-gray-400">
          Tract details, simulation results, equity warnings, and mitigation
          recommendations will appear here.
        </p>
      </aside>
    </div>
  );
}
