"""Ingest CDC/ATSDR Social Vulnerability Index data for Virginia census tracts."""

import os
import sys

import pandas as pd
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL, RAW_DIR, STATE_FIPS

# SVI 2022 data URL (CSV download)
SVI_URL = "https://svi.cdc.gov/Documents/Data/2022/csv/states/SVI_2022_US.csv"


def download_svi() -> str:
    """Download SVI data CSV."""
    os.makedirs(RAW_DIR, exist_ok=True)
    filepath = os.path.join(RAW_DIR, "svi_2022.csv")

    if os.path.exists(filepath):
        print("SVI file already downloaded, using cached version")
        return filepath

    print(f"Downloading SVI data from CDC...")
    resp = requests.get(SVI_URL, timeout=120)
    resp.raise_for_status()

    with open(filepath, "wb") as f:
        f.write(resp.content)

    print(f"Downloaded SVI data ({len(resp.content) / 1024 / 1024:.1f} MB)")
    return filepath


def run():
    """Ingest SVI data for Virginia tracts."""
    filepath = download_svi()
    engine = create_engine(DATABASE_URL)

    print("Parsing SVI data...")
    df = pd.read_csv(filepath, dtype={"FIPS": str})

    # Filter to Virginia (state FIPS 51)
    df = df[df["ST_ABBR"] == "VA"].copy()
    print(f"Found {len(df)} Virginia tracts in SVI data")

    # Relevant columns:
    # RPL_THEMES = Overall SVI percentile ranking
    # RPL_THEME1 = Socioeconomic
    # RPL_THEME2 = Household Composition & Disability
    # RPL_THEME3 = Minority Status & Language
    # RPL_THEME4 = Housing Type & Transportation

    with engine.begin() as conn:
        count = 0
        for _, row in df.iterrows():
            geoid = str(row["FIPS"]).zfill(11)

            # Check tract exists
            exists = conn.execute(
                text("SELECT 1 FROM census_tracts WHERE geoid = :geoid"),
                {"geoid": geoid},
            ).fetchone()
            if not exists:
                continue

            svi_overall = row.get("RPL_THEMES", -1)
            svi_socioeconomic = row.get("RPL_THEME1", -1)
            svi_household = row.get("RPL_THEME2", -1)
            svi_minority = row.get("RPL_THEME3", -1)
            svi_housing = row.get("RPL_THEME4", -1)

            # SVI uses -999 for missing values
            def clean(v):
                return None if v == -999 or v < 0 else round(float(v), 4)

            conn.execute(
                text("""
                    INSERT INTO tract_indicators (geoid, data_year, source,
                        svi_overall, svi_socioeconomic, svi_household_comp,
                        svi_minority, svi_housing_transport)
                    VALUES (:geoid, 2022, 'svi',
                        :svi_overall, :svi_socioeconomic, :svi_household_comp,
                        :svi_minority, :svi_housing_transport)
                    ON CONFLICT (geoid, data_year, source) DO UPDATE SET
                        svi_overall = :svi_overall,
                        svi_socioeconomic = :svi_socioeconomic,
                        svi_household_comp = :svi_household_comp,
                        svi_minority = :svi_minority,
                        svi_housing_transport = :svi_housing_transport
                """),
                {
                    "geoid": geoid,
                    "svi_overall": clean(svi_overall),
                    "svi_socioeconomic": clean(svi_socioeconomic),
                    "svi_household_comp": clean(svi_household),
                    "svi_minority": clean(svi_minority),
                    "svi_housing_transport": clean(svi_housing),
                },
            )
            count += 1

    print(f"Inserted SVI data for {count} Virginia tracts")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    run()
