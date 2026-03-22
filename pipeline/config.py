import os

# All US state/territory FIPS codes
ALL_STATE_FIPS = [
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12",
    "13", "15", "16", "17", "18", "19", "20", "21", "22", "23",
    "24", "25", "26", "27", "28", "29", "30", "31", "32", "33",
    "34", "35", "36", "37", "38", "39", "40", "41", "42", "44",
    "45", "46", "47", "48", "49", "50", "51", "53", "54", "55",
    "56", "60", "66", "69", "72", "78",
]

# Legacy — kept for backward compat but no longer used as a filter
STATE_FIPS = "51"

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://greenwatch:greenwatch@localhost:5432/greenwatch"
)

# Census API
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "")
CENSUS_BASE_URL = "https://api.census.gov/data"

# ACS 5-Year vintage years to ingest (for time-series analysis)
ACS_YEARS = [2019, 2020, 2021, 2022, 2023]

# Data directories
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# Scoring parameters
DRS_WEIGHTS = {
    "vulnerability": 0.40,
    "market_pressure": 0.35,
    "green_proximity": 0.25,
}

EBS_WEIGHTS = {
    "air_quality": 0.30,
    "green_infra": 0.30,
    "climate_resilience": 0.25,
    "health": 0.15,
}

# Intervention impact radii (meters)
IMPACT_RADII = {
    "park": 1500,
    "greenway": 1000,
    "transit_stop": 800,
    "tree_planting": 500,
    "flood_infrastructure": 2000,
    "green_roof": 300,
}

# Mitigation DRS reduction ranges (min, max points)
MITIGATION_EFFECTS = {
    "rent_stabilization": (15, 25),
    "community_land_trust": (20, 30),
    "affordable_housing": (10, 20),
    "community_benefit_agreement": (5, 15),
}
