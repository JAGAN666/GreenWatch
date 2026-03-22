"""Load all US census tract geometries from TIGER/Line shapefiles into PostGIS."""

import json
import glob
import os
import subprocess
import sys
import zipfile

from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL

# Path where user downloaded all state tract ZIPs
TRACTS_DIR = "/Users/jagan/Downloads/census_tracts"


def run():
    """Load all US tract shapefiles into PostGIS."""
    engine = create_engine(DATABASE_URL)

    # Find all ZIP files
    zip_files = sorted(glob.glob(os.path.join(TRACTS_DIR, "tl_2023_*_tract.zip")))
    print(f"Found {len(zip_files)} state tract shapefiles")

    if not zip_files:
        print(f"ERROR: No ZIP files found in {TRACTS_DIR}")
        return

    # Install pyshp if needed
    try:
        import shapefile
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyshp"], check=True)
        import shapefile

    # Clear existing tracts (cascade will clear dependent tables)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM simulation_tract_results"))
        conn.execute(text("DELETE FROM simulation_results"))
        conn.execute(text("DELETE FROM mitigations"))
        conn.execute(text("DELETE FROM interventions"))
        conn.execute(text("DELETE FROM scenarios"))
        conn.execute(text("DELETE FROM tract_scores"))
        conn.execute(text("DELETE FROM tract_indicators"))
        conn.execute(text("DELETE FROM census_tracts"))
        print("Cleared existing data")

    total_loaded = 0

    for zip_path in zip_files:
        state_fips = os.path.basename(zip_path).split("_")[2]
        extract_dir = os.path.join(TRACTS_DIR, f"extracted_{state_fips}")
        os.makedirs(extract_dir, exist_ok=True)

        # Extract
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        # Find .shp file
        shp_files = glob.glob(os.path.join(extract_dir, "*.shp"))
        if not shp_files:
            print(f"  {state_fips}: No .shp found, skipping")
            continue

        sf = shapefile.Reader(shp_files[0])
        features = sf.__geo_interface__["features"]

        with engine.begin() as conn:
            count = 0
            for feature in features:
                props = feature["properties"]
                geoid = props.get("GEOID", "")
                if not geoid:
                    continue

                county_fips = props.get("COUNTYFP", geoid[2:5])
                tract_fips = props.get("TRACTCE", geoid[5:])
                name = props.get("NAME", "")
                aland = props.get("ALAND", 0) or 0
                awater = props.get("AWATER", 0) or 0
                geom_json = json.dumps(feature["geometry"])

                conn.execute(
                    text("""
                        INSERT INTO census_tracts (geoid, state_fips, county_fips, tract_fips,
                            name, county_name, aland, awater, geom, centroid)
                        VALUES (:geoid, :state_fips, :county_fips, :tract_fips,
                            :name, '', :aland, :awater,
                            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                            ST_Centroid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)))
                        ON CONFLICT (geoid) DO NOTHING
                    """),
                    {
                        "geoid": geoid,
                        "state_fips": state_fips,
                        "county_fips": county_fips,
                        "tract_fips": tract_fips,
                        "name": name,
                        "aland": int(aland),
                        "awater": int(awater),
                        "geom": geom_json,
                    },
                )
                count += 1

            total_loaded += count

        print(f"  {state_fips}: {count} tracts loaded ({total_loaded} total)")

    # Verify
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM census_tracts")).scalar()
        print(f"\nTotal tracts in database: {result}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    run()
