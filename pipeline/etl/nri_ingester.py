"""Ingest FEMA National Risk Index data for Virginia census tracts.

Uses the NRI v1.20 (Dec 2025) census tract CSV from FEMA.
"""

import os
import sys
import zipfile

import pandas as pd
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL, RAW_DIR, STATE_FIPS

NRI_URL = "https://www.fema.gov/about/reports-and-data/openfema/nri/v120/NRI_Table_CensusTracts.zip"


def download_nri() -> str:
    os.makedirs(RAW_DIR, exist_ok=True)
    csv_path = os.path.join(RAW_DIR, "NRI_Table_CensusTracts.csv")

    if os.path.exists(csv_path):
        print("NRI CSV already extracted, using cached version")
        return csv_path

    zip_path = os.path.join(RAW_DIR, "NRI_Table_CensusTracts.zip")
    if not os.path.exists(zip_path):
        print("Downloading FEMA NRI data (634 MB)...")
        resp = requests.get(NRI_URL, timeout=600, stream=True)
        resp.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)

    print("Extracting NRI CSV from ZIP...")
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if csv_names:
            with zf.open(csv_names[0]) as f:
                with open(csv_path, "wb") as out:
                    out.write(f.read())
            print(f"Extracted {csv_names[0]}")

    return csv_path


def run():
    filepath = download_nri()
    engine = create_engine(DATABASE_URL)

    print("Parsing NRI data...")
    df = pd.read_csv(filepath, dtype={"TRACTFIPS": str}, low_memory=False)

    # Filter to Virginia
    df = df[df["STATEABBRV"] == "VA"].copy()
    print(f"Found {len(df)} Virginia tracts in NRI data")

    # Print available risk columns
    risk_cols = [c for c in df.columns if c.endswith("_RISKS") or c == "RISK_SCORE"]
    print(f"  Available risk columns: {risk_cols[:10]}")

    with engine.begin() as conn:
        # Remove old proxy data
        conn.execute(text("DELETE FROM tract_indicators WHERE source IN ('nri', 'nri_proxy')"))

        count = 0
        for _, row in df.iterrows():
            geoid = str(row["TRACTFIPS"]).zfill(11)

            exists = conn.execute(
                text("SELECT 1 FROM census_tracts WHERE geoid = :geoid"),
                {"geoid": geoid},
            ).fetchone()
            if not exists:
                continue

            def safe_float(col):
                try:
                    v = float(row.get(col, None))
                    return None if pd.isna(v) else round(v, 4)
                except (ValueError, TypeError):
                    return None

            conn.execute(
                text("""
                    INSERT INTO tract_indicators (geoid, data_year, source,
                        nri_risk_score, nri_flood_score, nri_heat_score, nri_hurricane_score)
                    VALUES (:geoid, 2025, 'nri',
                        :nri_risk_score, :nri_flood_score, :nri_heat_score, :nri_hurricane_score)
                    ON CONFLICT (geoid, data_year, source) DO UPDATE SET
                        nri_risk_score = :nri_risk_score,
                        nri_flood_score = :nri_flood_score,
                        nri_heat_score = :nri_heat_score,
                        nri_hurricane_score = :nri_hurricane_score
                """),
                {
                    "geoid": geoid,
                    "nri_risk_score": safe_float("RISK_SCORE"),
                    "nri_flood_score": safe_float("RFLD_RISKS"),
                    "nri_heat_score": safe_float("HWAV_RISKS"),
                    "nri_hurricane_score": safe_float("HRCN_RISKS"),
                },
            )
            count += 1

    print(f"Loaded real NRI data for {count} Virginia tracts")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    run()
