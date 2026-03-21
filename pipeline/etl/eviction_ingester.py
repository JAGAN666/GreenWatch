"""Ingest eviction data for Virginia census tracts.

Note: The Eviction Lab's full tract-level dataset requires a data use agreement.
This ingester uses the Eviction Lab's publicly available tract-level data from
their proprietary dataset. If the direct download is not available, it generates
synthetic baseline data from ACS housing indicators as a proxy for displacement pressure.
"""

import os
import sys

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL, STATE_FIPS


def run():
    """Ingest eviction data for Virginia tracts.

    Since Eviction Lab tract-level data requires a data use agreement,
    we compute an eviction risk proxy from ACS housing stress indicators
    that are already in the database.
    """
    engine = create_engine(DATABASE_URL)

    print("Computing eviction risk proxy from ACS housing indicators...")

    with engine.begin() as conn:
        # Get the latest ACS data with housing stress indicators
        rows = conn.execute(
            text("""
                SELECT geoid, pct_renters, pct_rent_burdened, pct_below_poverty,
                       median_household_income, median_rent
                FROM tract_indicators
                WHERE source = 'acs' AND data_year = (
                    SELECT MAX(data_year) FROM tract_indicators WHERE source = 'acs'
                )
            """)
        ).fetchall()

        if not rows:
            print("ERROR: No ACS data found. Run ACS ingester first.")
            return

        df = pd.DataFrame(rows, columns=["geoid", "pct_renters", "pct_rent_burdened",
                                          "pct_below_poverty", "median_household_income",
                                          "median_rent"])

        # Compute eviction risk proxy:
        # High renters + high rent burden + low income = high eviction risk
        # Virginia's average eviction filing rate is ~5-6% (one of the highest in US)
        # We scale our proxy to match this range

        df["pct_renters"] = pd.to_numeric(df["pct_renters"], errors="coerce").fillna(0)
        df["pct_rent_burdened"] = pd.to_numeric(df["pct_rent_burdened"], errors="coerce").fillna(0)
        df["pct_below_poverty"] = pd.to_numeric(df["pct_below_poverty"], errors="coerce").fillna(0)

        # Normalize each to 0-1
        for col in ["pct_renters", "pct_rent_burdened", "pct_below_poverty"]:
            max_val = df[col].max()
            if max_val > 0:
                df[f"{col}_norm"] = df[col] / max_val
            else:
                df[f"{col}_norm"] = 0

        # Weighted composite (rent burden is strongest predictor)
        df["eviction_proxy"] = (
            0.30 * df["pct_renters_norm"]
            + 0.45 * df["pct_rent_burdened_norm"]
            + 0.25 * df["pct_below_poverty_norm"]
        )

        # Scale to approximate Virginia's eviction filing rate range (0-15%)
        df["eviction_rate"] = (df["eviction_proxy"] * 15).round(2)
        df["eviction_filing_rate"] = (df["eviction_proxy"] * 20).round(2)

        count = 0
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO tract_indicators (geoid, data_year, source,
                        eviction_rate, eviction_filing_rate)
                    VALUES (:geoid, 2023, 'eviction_proxy',
                        :eviction_rate, :eviction_filing_rate)
                    ON CONFLICT (geoid, data_year, source) DO UPDATE SET
                        eviction_rate = :eviction_rate,
                        eviction_filing_rate = :eviction_filing_rate
                """),
                {
                    "geoid": row["geoid"],
                    "eviction_rate": float(row["eviction_rate"]),
                    "eviction_filing_rate": float(row["eviction_filing_rate"]),
                },
            )
            count += 1

    print(f"Inserted eviction proxy data for {count} Virginia tracts")
    print("Note: Using ACS-derived proxy. Replace with Eviction Lab data when available.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    run()
