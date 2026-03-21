const SCORING_URL =
  process.env.SCORING_SERVICE_URL || "http://localhost:8000";

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
  const res = await fetch(`${SCORING_URL}/scoring/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Scoring service error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getTractScoring(geoid: string) {
  const res = await fetch(`${SCORING_URL}/scoring/tract/${geoid}`);
  if (!res.ok) {
    throw new Error(`Scoring service error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function recomputeScores() {
  const res = await fetch(`${SCORING_URL}/scoring/recompute`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Scoring service error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
