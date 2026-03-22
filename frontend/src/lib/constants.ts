export const STATE_NAMES: Record<string, string> = {
  "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas",
  "06": "California", "08": "Colorado", "09": "Connecticut", "10": "Delaware",
  "11": "District of Columbia", "12": "Florida", "13": "Georgia", "15": "Hawaii",
  "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa",
  "20": "Kansas", "21": "Kentucky", "22": "Louisiana", "23": "Maine",
  "24": "Maryland", "25": "Massachusetts", "26": "Michigan", "27": "Minnesota",
  "28": "Mississippi", "29": "Missouri", "30": "Montana", "31": "Nebraska",
  "32": "Nevada", "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico",
  "36": "New York", "37": "North Carolina", "38": "North Dakota", "39": "Ohio",
  "40": "Oklahoma", "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island",
  "45": "South Carolina", "46": "South Dakota", "47": "Tennessee", "48": "Texas",
  "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
  "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming",
  "60": "American Samoa", "66": "Guam", "69": "Northern Mariana Islands",
  "72": "Puerto Rico", "78": "US Virgin Islands",
};

export function getStateName(geoid: string): string {
  return STATE_NAMES[geoid.substring(0, 2)] || "";
}

export function getDisplayName(county: string, geoid: string): string {
  const state = getStateName(geoid);
  if (county) return `${county}, ${state}`;
  return state || `Tract ${geoid}`;
}

export const INTERVENTION_TYPES = [
  { value: "park", label: "Park", unit: "acres", icon: "park", color: "#22c55e" },
  { value: "greenway", label: "Greenway", unit: "miles", icon: "greenway", color: "#84cc16" },
  { value: "transit_stop", label: "Transit Stop", unit: "stops", icon: "transit", color: "#3b82f6" },
  { value: "tree_planting", label: "Tree Planting", unit: "trees", icon: "tree", color: "#166534" },
  { value: "flood_infrastructure", label: "Flood Protection", unit: "acres", icon: "flood", color: "#22d3ee" },
  { value: "green_roof", label: "Green Roof", unit: "buildings", icon: "roof", color: "#14b8a6" },
] as const;

export const IMPACT_RADII: Record<string, number> = {
  park: 1500, greenway: 1000, transit_stop: 800,
  tree_planting: 500, flood_infrastructure: 2000, green_roof: 500,
};

export const POLICY_OPTIONS = [
  { value: "rent_stabilization", label: "Rent Stabilization", description: "Cap rent increases in affected areas" },
  { value: "community_land_trust", label: "Community Land Trust", description: "Remove land from speculative market" },
  { value: "affordable_housing", label: "Affordable Housing Mandate", description: "Require 20%+ affordable units" },
  { value: "community_benefit_agreement", label: "Community Benefit Agreement", description: "Binding commitments to residents" },
] as const;
