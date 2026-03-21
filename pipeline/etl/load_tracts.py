"""Load Virginia census tract geometries from Census TIGER/Line into PostGIS."""

import json
import os
import subprocess
import sys
import zipfile
from io import BytesIO

import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL, STATE_FIPS

TIGER_URL = f"https://www2.census.gov/geo/tiger/TIGER2023/TRACT/tl_2023_{STATE_FIPS}_tract.zip"


def download_and_extract():
    """Download Virginia tract shapefile from Census TIGER/Line."""
    extract_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "tracts")
    shp_path = os.path.join(extract_dir, f"tl_2023_{STATE_FIPS}_tract.shp")

    if os.path.exists(shp_path):
        print("Shapefile already downloaded, using cached version")
        return extract_dir

    print(f"Downloading Virginia tract boundaries...")
    os.makedirs(extract_dir, exist_ok=True)
    resp = requests.get(TIGER_URL, timeout=120)
    resp.raise_for_status()

    with zipfile.ZipFile(BytesIO(resp.content)) as zf:
        zf.extractall(extract_dir)

    print(f"Extracted to {extract_dir}")
    return extract_dir


def load_tracts_via_docker(extract_dir: str):
    """Load shapefile into PostGIS using ogr2ogr inside the Docker container."""
    shp_file = f"tl_2023_{STATE_FIPS}_tract.shp"
    container_path = "/tmp/tracts"

    print("Loading shapefile into PostGIS via ogr2ogr...")

    # Copy shapefile to Docker container
    subprocess.run(
        ["docker", "cp", f"{extract_dir}/.", "greenwatch-db-1:/tmp/tracts/"],
        check=True,
    )

    # Use ogr2ogr inside the container to load shapefile
    # First check if ogr2ogr is available
    result = subprocess.run(
        ["docker", "exec", "greenwatch-db-1", "which", "ogr2ogr"],
        capture_output=True, text=True,
    )

    if result.returncode == 0:
        # ogr2ogr is available in the PostGIS container
        subprocess.run(
            [
                "docker", "exec", "greenwatch-db-1",
                "ogr2ogr",
                "-f", "PostgreSQL",
                "PG:dbname=greenwatch user=greenwatch password=greenwatch",
                f"{container_path}/{shp_file}",
                "-nln", "tiger_tracts_raw",
                "-overwrite",
                "-t_srs", "EPSG:4326",
            ],
            check=True,
        )

        # Now copy from raw table to our census_tracts table
        engine = create_engine(DATABASE_URL)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM census_tracts"))

            # Get county names
            county_names = get_county_names()

            count = conn.execute(
                text("""
                    INSERT INTO census_tracts (geoid, state_fips, county_fips, tract_fips,
                        name, county_name, aland, awater, geom, centroid)
                    SELECT
                        geoid,
                        statefp,
                        countyfp,
                        tractce,
                        name,
                        '',
                        aland,
                        awater,
                        ST_Multi(wkb_geometry),
                        ST_Centroid(wkb_geometry)
                    FROM tiger_tracts_raw
                    ON CONFLICT (geoid) DO UPDATE SET
                        geom = EXCLUDED.geom,
                        centroid = EXCLUDED.centroid
                """)
            ).rowcount

            # Update county names
            for county_fips, county_name in county_names.items():
                conn.execute(
                    text("UPDATE census_tracts SET county_name = :name WHERE county_fips = :fips"),
                    {"name": county_name, "fips": county_fips},
                )

            # Clean up raw table
            conn.execute(text("DROP TABLE IF EXISTS tiger_tracts_raw"))

            print(f"Loaded {count} Virginia census tracts into PostGIS")
    else:
        print("ogr2ogr not available in container, using Python fallback...")
        load_tracts_python(extract_dir)


def load_tracts_python(extract_dir: str):
    """Load shapefile using Python (dbfread for attributes, manual geometry)."""
    import struct

    engine = create_engine(DATABASE_URL)
    shp_path = os.path.join(extract_dir, f"tl_2023_{STATE_FIPS}_tract.shp")
    dbf_path = os.path.join(extract_dir, f"tl_2023_{STATE_FIPS}_tract.dbf")

    # Read DBF for attributes
    try:
        from dbfread import DBF
    except ImportError:
        # Install dbfread
        subprocess.run([sys.executable, "-m", "pip", "install", "dbfread"], check=True)
        from dbfread import DBF

    table = DBF(dbf_path, encoding="utf-8")
    county_names = get_county_names()

    # We need to read the shapefile geometry too
    # Use a simple approach: convert shapefile to GeoJSON using ogr2ogr locally
    try:
        # Try using ogr2ogr if available locally
        geojson_path = os.path.join(extract_dir, "tracts.geojson")
        subprocess.run(
            ["ogr2ogr", "-f", "GeoJSON", geojson_path, shp_path, "-t_srs", "EPSG:4326"],
            check=True, capture_output=True,
        )

        with open(geojson_path) as f:
            geojson_data = json.load(f)

        load_from_geojson_features(geojson_data["features"], engine, county_names)
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try pyshp
    try:
        import shapefile
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyshp"], check=True)
        import shapefile

    print("Reading shapefile with pyshp...")
    sf = shapefile.Reader(shp_path)
    features = sf.__geo_interface__["features"]
    load_from_geojson_features(features, engine, county_names)


def load_from_geojson_features(features: list, engine, county_names: dict):
    """Load GeoJSON features into census_tracts table."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM census_tracts"))

        count = 0
        for feature in features:
            props = feature["properties"]
            geoid = props.get("GEOID", "")
            if not geoid:
                continue

            county_fips = props.get("COUNTYFP", geoid[2:5])
            tract_fips = props.get("TRACTCE", geoid[5:])
            name = props.get("NAME", "")
            county_name = county_names.get(county_fips, "")
            aland = props.get("ALAND", 0) or 0
            awater = props.get("AWATER", 0) or 0
            geom_json = json.dumps(feature["geometry"])

            conn.execute(
                text("""
                    INSERT INTO census_tracts (geoid, state_fips, county_fips, tract_fips,
                        name, county_name, aland, awater, geom, centroid)
                    VALUES (:geoid, :state_fips, :county_fips, :tract_fips,
                        :name, :county_name, :aland, :awater,
                        ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                        ST_Centroid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)))
                    ON CONFLICT (geoid) DO UPDATE SET
                        geom = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                        centroid = ST_Centroid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                        county_name = :county_name
                """),
                {
                    "geoid": geoid,
                    "state_fips": STATE_FIPS,
                    "county_fips": county_fips,
                    "tract_fips": tract_fips,
                    "name": name,
                    "county_name": county_name,
                    "aland": int(aland),
                    "awater": int(awater),
                    "geom": geom_json,
                },
            )
            count += 1

        print(f"Loaded {count} Virginia census tracts into PostGIS")

    # Verify
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM census_tracts")).scalar()
        print(f"Verification: {result} tracts in database")


def get_county_names() -> dict:
    """Fetch Virginia county FIPS to name mapping from Census API."""
    api_key = os.getenv("CENSUS_API_KEY", "")
    url = (
        f"https://api.census.gov/data/2023/acs/acs5"
        f"?get=NAME&for=county:*&in=state:{STATE_FIPS}"
    )
    if api_key:
        url += f"&key={api_key}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {row[2]: row[0].split(",")[0] for row in data[1:]}
    except Exception as e:
        print(f"Warning: Could not fetch county names: {e}")
        return {}


def run():
    """Main entry point."""
    extract_dir = download_and_extract()
    load_tracts_via_docker(extract_dir)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    run()
