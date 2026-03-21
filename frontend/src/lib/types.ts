import type { Geometry, Polygon } from "geojson";

export interface TractProperties {
  geoid: string;
  county_name: string;
  name: string;
  // Displacement Risk Score
  drs_composite: number;
  drs_vulnerability: number;
  drs_market_pressure: number;
  drs_green_proximity: number;
  drs_classification: "low" | "moderate" | "high" | "critical";
  // Environmental Benefit Score
  ebs_composite: number;
  ebs_air_quality: number;
  ebs_green_infra: number;
  ebs_climate_resilience: number;
  ebs_health: number;
  // Key indicators
  median_rent: number | null;
  median_home_value: number | null;
  median_household_income: number | null;
  pct_renters: number | null;
  pct_rent_burdened: number | null;
  pct_nonwhite: number | null;
  total_population: number | null;
  asthma_prevalence: number | null;
  eviction_rate: number | null;
  tree_canopy_pct: number | null;
  // Flags
  cejst_disadvantaged: boolean;
  accelerating_risk: boolean;
}

export interface TractFeature {
  type: "Feature";
  geometry: Geometry;
  properties: TractProperties;
}

export interface TractFeatureCollection {
  type: "FeatureCollection";
  features: TractFeature[];
}

export type InterventionType =
  | "park"
  | "greenway"
  | "transit_stop"
  | "tree_planting"
  | "flood_infrastructure"
  | "green_roof";

export interface Intervention {
  id: string;
  type: InterventionType;
  location: { lat: number; lng: number };
  polygon?: Polygon;
  scale_value: number;
  scale_unit: string;
  parameters?: Record<string, unknown>;
}

export type MitigationType =
  | "rent_stabilization"
  | "community_land_trust"
  | "affordable_housing"
  | "community_benefit_agreement";

export interface Mitigation {
  id: string;
  type: MitigationType;
  target_geoids: string[];
  parameters?: Record<string, unknown>;
}

export interface Scenario {
  id: string;
  title: string;
  description: string;
  status: "draft" | "simulated" | "published" | "archived";
  interventions: Intervention[];
  mitigations: Mitigation[];
  created_at: string;
  updated_at: string;
}

export interface SimulationTractResult {
  geoid: string;
  current_drs: number;
  predicted_drs: number;
  delta_drs: number;
  current_ebs: number;
  predicted_ebs: number;
  delta_ebs: number;
  confidence_lower: number;
  confidence_upper: number;
  equity_warning: boolean;
}

export interface SimulationResult {
  id: string;
  scenario_id: string;
  total_population_affected: number;
  total_tracts_affected: number;
  equity_warnings_count: number;
  equity_score: number;
  summary_text: string;
  tract_results: SimulationTractResult[];
}
