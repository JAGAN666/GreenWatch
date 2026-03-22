// All scoring calls go through Next.js API routes (same-origin, no CORS issues)

export async function simulateScenario(payload: {
  interventions: Array<{
    type: string;
    lat: number;
    lng: number;
    scale_value: number;
    scale_unit: string;
    parameters?: Record<string, unknown>;
  }>;
  mitigations?: Array<{
    type: string;
    target_geoids: string[];
    parameters?: Record<string, unknown>;
  }>;
}) {
  const res = await fetch("/api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `Simulation failed: ${res.status}`);
  }
  return res.json();
}

export async function optimizeScenario(payload: {
  type: string;
  scale_value: number;
  scale_unit: string;
  min_lat: number;
  min_lng: number;
  max_lat: number;
  max_lng: number;
}) {
  const res = await fetch("/api/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `Optimization failed: ${res.status}`);
  }
  return res.json();
}

export async function getTractScoring(geoid: string) {
  const res = await fetch(`/api/tract/${geoid}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch tract: ${res.status}`);
  }
  return res.json();
}

export async function recomputeScores() {
  const res = await fetch("/api/recompute", { method: "POST" });
  if (!res.ok) {
    throw new Error(`Recompute failed: ${res.status}`);
  }
  return res.json();
}
