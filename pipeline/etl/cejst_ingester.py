"""Ingest CEJST (Justice40) disadvantaged community data for Virginia.

Uses v2.0 data from community mirror (original site taken offline Jan 2025).
"""

import os
import sys

import pandas as pd
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL, RAW_DIR, STATE_FIPS

CEJST_URL = "https://dblew8dgr6ajz.cloudfront.net/data-versions/2.0/data/score/downloadable/2.0-communities.csv"


def download_cejst() -> str:
    os.makedirs(RAW_DIR, exist_ok=True)
    filepath = os.path.join(RAW_DIR, "cejst_communities.csv")
    if os.path.exists(filepath):
        print("CEJST file already downloaded, using cached version")
        return filepath

    print("Downloading CEJST v2.0 data from community mirror...")
    resp = requests.get(CEJST_URL, timeout=300, stream=True)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded CEJST data ({os.path.getsize(filepath) / 1024 / 1024:.1f} MB)")
    return filepath


def run():
    filepath = download_cejst()
    engine = create_engine(DATABASE_URL)

    print("Parsing CEJST data...")
    df = pd.read_csv(
        filepath,
        dtype={"Census tract 2010 ID": str},
        low_memory=False,
        usecols=[
            "Census tract 2010 ID",
            "State/Territory",
            "Identified as disadvantaged",
            "Total threshold criteria exceeded",
        ],
    )

    # No state filter — load all US tracts
    print(f"Found {len(df)} US tracts in CEJST v2.0 data")

    with engine.begin() as conn:
        # Remove old proxy data
        conn.execute(text("DELETE FROM tract_indicators WHERE source IN ('cejst', 'cejst_proxy')"))

        count = 0
        disadvantaged_count = 0

        for _, row in df.iterrows():
            geoid_2010 = str(row["Census tract 2010 ID"]).zfill(11)
            is_disadvantaged = row.get("Identified as disadvantaged", False)
            if isinstance(is_disadvantaged, str):
                is_disadvantaged = is_disadvantaged.strip().lower() == "true"

            # CEJST uses 2010 tract IDs; our DB has 2020. Try exact match first.
            exists = conn.execute(
                text("SELECT geoid FROM census_tracts WHERE geoid = :geoid"),
                {"geoid": geoid_2010},
            ).fetchone()

            if not exists:
                # Try prefix match (county + first 4 digits of tract)
                prefix = geoid_2010[:9]
                exists = conn.execute(
                    text("SELECT geoid FROM census_tracts WHERE geoid LIKE :prefix LIMIT 1"),
                    {"prefix": prefix + "%"},
                ).fetchone()

            if not exists:
                continue

            actual_geoid = exists[0]

            conn.execute(
                text("""
                    INSERT INTO tract_indicators (geoid, data_year, source, cejst_disadvantaged)
                    VALUES (:geoid, 2024, 'cejst', :disadvantaged)
                    ON CONFLICT (geoid, data_year, source) DO UPDATE SET
                        cejst_disadvantaged = :disadvantaged
                """),
                {"geoid": actual_geoid, "disadvantaged": bool(is_disadvantaged)},
            )
            count += 1
            if is_disadvantaged:
                disadvantaged_count += 1

    print(f"Loaded real CEJST data for {count} tracts ({disadvantaged_count} disadvantaged)")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    run()
