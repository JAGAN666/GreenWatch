"""Ingest CDC PLACES health data for Virginia census tracts.

Uses the 2024 release archived on Zenodo (CDC data.cdc.gov is currently 503).
"""

import os
import sys

import pandas as pd
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL, RAW_DIR, STATE_FIPS

PLACES_ZENODO_URL = "https://zenodo.org/records/14774046/files/PLACES__Local_Data_for_Better_Health__Census_Tract_Data_2024_release.csv?download=1"


def download_places() -> str:
    os.makedirs(RAW_DIR, exist_ok=True)
    filepath = os.path.join(RAW_DIR, "places_tract.csv")

    if os.path.exists(filepath) and os.path.getsize(filepath) > 100_000_000:
        print("PLACES file already downloaded, using cached version")
        return filepath

    print("Downloading CDC PLACES 2024 from Zenodo (761 MB)...")
    resp = requests.get(PLACES_ZENODO_URL, timeout=600, stream=True)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
    print(f"Downloaded PLACES data ({os.path.getsize(filepath) / 1024 / 1024:.0f} MB)")
    return filepath


def run():
    filepath = download_places()
    engine = create_engine(DATABASE_URL)

    print("Parsing PLACES data for Virginia (reading in chunks)...")

    # Detect column names from first few rows
    sample = pd.read_csv(filepath, nrows=5)
    cols = sample.columns.tolist()

    # Find the right column names (may vary between releases)
    loc_col = next((c for c in cols if c.lower() in ("locationid", "tractfips", "geoid")), None)
    state_col = next((c for c in cols if c.lower() in ("stateabbr", "stateabbreviation")), None)
    measure_col = next((c for c in cols if c.lower() in ("measureid", "measure_id")), None)
    if not measure_col:
        measure_col = next((c for c in cols if c.lower() == "measure"), None)
    value_col = next((c for c in cols if c.lower() in ("data_value", "datavalue")), None)
    type_col = next((c for c in cols if "value_type" in c.lower() or "valuetype" in c.lower()), None)

    print(f"  Columns detected: loc={loc_col}, state={state_col}, measure={measure_col}, value={value_col}, type={type_col}")

    if not all([loc_col, measure_col, value_col]):
        print(f"ERROR: Could not detect required columns. Available: {cols[:15]}")
        return

    with engine.begin() as conn:
        # Remove old proxy data
        conn.execute(text("DELETE FROM tract_indicators WHERE source IN ('places', 'places_proxy')"))

        count = 0
        chunks = pd.read_csv(filepath, dtype={loc_col: str}, low_memory=False, chunksize=100000)

        tract_data = {}  # geoid -> {asthma: val, mental: val}

        for chunk in chunks:
            # Filter to Virginia
            if state_col:
                va_chunk = chunk[chunk[state_col] == "VA"]
            else:
                va_chunk = chunk[chunk[loc_col].str.startswith(STATE_FIPS, na=False)]

            if va_chunk.empty:
                continue

            # Filter to crude prevalence if type column exists
            if type_col:
                va_chunk = va_chunk[va_chunk[type_col].str.contains("Crude", case=False, na=False)]

            for _, row in va_chunk.iterrows():
                geoid = str(row[loc_col]).zfill(11)
                measure = str(row[measure_col]).upper()
                value = pd.to_numeric(row[value_col], errors="coerce")

                if pd.isna(value):
                    continue

                if geoid not in tract_data:
                    tract_data[geoid] = {}

                if "ASTHMA" in measure or measure == "CASTHMA":
                    tract_data[geoid]["asthma"] = float(value)
                elif "MHLTH" in measure or "MENTAL" in measure:
                    tract_data[geoid]["mental"] = float(value)

        print(f"  Parsed {len(tract_data)} Virginia tracts from PLACES data")

        for geoid, data in tract_data.items():
            exists = conn.execute(
                text("SELECT 1 FROM census_tracts WHERE geoid = :geoid"),
                {"geoid": geoid},
            ).fetchone()
            if not exists:
                continue

            conn.execute(
                text("""
                    INSERT INTO tract_indicators (geoid, data_year, source,
                        asthma_prevalence, mental_health_not_good)
                    VALUES (:geoid, 2024, 'places',
                        :asthma, :mental_health)
                    ON CONFLICT (geoid, data_year, source) DO UPDATE SET
                        asthma_prevalence = :asthma,
                        mental_health_not_good = :mental_health
                """),
                {
                    "geoid": geoid,
                    "asthma": data.get("asthma"),
                    "mental_health": data.get("mental"),
                },
            )
            count += 1

    print(f"Loaded real PLACES data for {count} Virginia tracts")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    run()
