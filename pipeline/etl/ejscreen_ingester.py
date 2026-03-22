"""Ingest EPA EJScreen environmental justice data for Virginia census tracts.

Uses the 2024 data archived on Zenodo (EPA removed public access Feb 2025).
The full archive is 5.2 GB. This ingester downloads and extracts only the
tract-level CSV.
"""

import os
import sys
import zipfile

import pandas as pd
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL, RAW_DIR, STATE_FIPS

EJSCREEN_ZENODO_URL = "https://zenodo.org/records/14767363/files/2024.zip?download=1"


def download_ejscreen() -> str:
    os.makedirs(RAW_DIR, exist_ok=True)
    csv_path = os.path.join(RAW_DIR, "ejscreen_tracts.csv")

    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 1_000_000:
        print("EJScreen CSV already extracted, using cached version")
        return csv_path

    zip_path = os.path.join(RAW_DIR, "ejscreen_2024.zip")
    if not os.path.exists(zip_path):
        print("Downloading EJScreen 2024 from Zenodo (5.2 GB — this will take a while)...")
        resp = requests.get(EJSCREEN_ZENODO_URL, timeout=1800, stream=True)
        resp.raise_for_status()
        downloaded = 0
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if downloaded % (100 * 1024 * 1024) == 0:
                    print(f"  Downloaded {downloaded / 1024 / 1024:.0f} MB...")
        print(f"Downloaded EJScreen archive ({downloaded / 1024 / 1024:.0f} MB)")

    print("Extracting tract CSV from EJScreen archive...")
    with zipfile.ZipFile(zip_path) as zf:
        # Find tract-level CSV
        tract_csvs = [n for n in zf.namelist()
                      if "tract" in n.lower() and n.endswith(".csv")]
        if not tract_csvs:
            # Try any CSV
            tract_csvs = [n for n in zf.namelist() if n.endswith(".csv")]

        if tract_csvs:
            print(f"  Extracting {tract_csvs[0]}...")
            with zf.open(tract_csvs[0]) as f:
                with open(csv_path, "wb") as out:
                    out.write(f.read())
        else:
            print(f"ERROR: No CSV found in archive. Contents: {zf.namelist()[:10]}")
            return ""

    return csv_path


def run():
    filepath = download_ejscreen()
    if not filepath or not os.path.exists(filepath):
        print("EJScreen data not available. Skipping.")
        return

    engine = create_engine(DATABASE_URL)

    print("Parsing EJScreen data...")
    df = pd.read_csv(filepath, dtype={"ID": str}, low_memory=False, nrows=5)
    cols = df.columns.tolist()

    # Find the GEOID column
    id_col = next((c for c in cols if c.upper() == "ID"), None)
    if not id_col:
        id_col = next((c for c in cols if "fips" in c.lower() or "geoid" in c.lower()), cols[0])

    # Find environmental indicator columns
    pm25_col = next((c for c in cols if "PM25" in c.upper() and "PCTILE" not in c.upper() and "PCT" not in c.upper()), None)
    ozone_col = next((c for c in cols if "OZONE" in c.upper() and "PCTILE" not in c.upper() and "PCT" not in c.upper()), None)
    diesel_col = next((c for c in cols if "DSLPM" in c.upper() or ("DIESEL" in c.upper() and "PCTILE" not in c.upper())), None)
    traffic_col = next((c for c in cols if "PTRAF" in c.upper() or ("TRAFFIC" in c.upper() and "PCTILE" not in c.upper())), None)
    lead_col = next((c for c in cols if "PRE1960" in c.upper() or "LDPNT" in c.upper()), None)

    print(f"  ID column: {id_col}")
    print(f"  PM2.5={pm25_col}, Ozone={ozone_col}, Diesel={diesel_col}, Traffic={traffic_col}, Lead={lead_col}")

    # Read full file now
    df = pd.read_csv(filepath, dtype={id_col: str}, low_memory=False)

    # No state filter — load all US tracts
    print(f"Found {len(df)} US tracts in EJScreen data")

    with engine.begin() as conn:
        # Remove old proxy data
        conn.execute(text("DELETE FROM tract_indicators WHERE source IN ('ejscreen', 'ejscreen_proxy')"))

        count = 0
        for _, row in df.iterrows():
            geoid = str(row[id_col]).zfill(11)

            exists = conn.execute(
                text("SELECT 1 FROM census_tracts WHERE geoid = :geoid"),
                {"geoid": geoid},
            ).fetchone()
            if not exists:
                continue

            def safe_float(col):
                if col is None:
                    return None
                try:
                    v = float(row[col])
                    return None if pd.isna(v) else round(v, 4)
                except (ValueError, TypeError, KeyError):
                    return None

            conn.execute(
                text("""
                    INSERT INTO tract_indicators (geoid, data_year, source,
                        pm25, ozone, diesel_pm, traffic_proximity, lead_paint)
                    VALUES (:geoid, 2024, 'ejscreen',
                        :pm25, :ozone, :diesel_pm, :traffic_proximity, :lead_paint)
                    ON CONFLICT (geoid, data_year, source) DO UPDATE SET
                        pm25 = :pm25, ozone = :ozone, diesel_pm = :diesel_pm,
                        traffic_proximity = :traffic_proximity, lead_paint = :lead_paint
                """),
                {
                    "geoid": geoid,
                    "pm25": safe_float(pm25_col),
                    "ozone": safe_float(ozone_col),
                    "diesel_pm": safe_float(diesel_col),
                    "traffic_proximity": safe_float(traffic_col),
                    "lead_paint": safe_float(lead_col),
                },
            )
            count += 1

    print(f"Loaded real EJScreen data for {count} Virginia tracts")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    run()
