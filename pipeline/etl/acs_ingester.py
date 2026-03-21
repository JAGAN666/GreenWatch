"""Ingest American Community Survey (ACS) 5-Year data for Virginia census tracts."""

import os
import sys

import pandas as pd
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ACS_YEARS, CENSUS_API_KEY, DATABASE_URL, STATE_FIPS

# ACS variable mapping: variable code -> (column_name, description)
ACS_VARIABLES = {
    "B25064_001E": ("median_rent", "Median gross rent"),
    "B25077_001E": ("median_home_value", "Median home value"),
    "B19013_001E": ("median_household_income", "Median household income"),
    "B25003_001E": ("_total_tenure", "Total housing units (tenure)"),
    "B25003_002E": ("_owner_occupied", "Owner-occupied units"),
    "B25003_003E": ("_renter_occupied", "Renter-occupied units"),
    "B25070_010E": ("_rent_burden_50plus", "Renters paying 50%+ income on rent"),
    "B25070_007E": ("_rent_burden_30_34", "Renters paying 30-34.9%"),
    "B25070_008E": ("_rent_burden_35_39", "Renters paying 35-39.9%"),
    "B25070_009E": ("_rent_burden_40_49", "Renters paying 40-49.9%"),
    "B25070_001E": ("_rent_burden_total", "Total renters for rent burden"),
    "B01003_001E": ("total_population", "Total population"),
    "B11001_001E": ("total_households", "Total households"),
    "B02001_001E": ("_race_total", "Total population (race)"),
    "B02001_002E": ("_race_white", "White alone"),
    "B17001_001E": ("_poverty_total", "Total for poverty status"),
    "B17001_002E": ("_poverty_below", "Below poverty level"),
    "B15003_001E": ("_edu_total", "Total population 25+ (education)"),
    "B15003_022E": ("_edu_bachelors", "Bachelor's degree"),
    "B15003_023E": ("_edu_masters", "Master's degree"),
    "B15003_024E": ("_edu_professional", "Professional degree"),
    "B15003_025E": ("_edu_doctorate", "Doctorate degree"),
}


def fetch_acs_year(year: int) -> pd.DataFrame:
    """Fetch ACS 5-Year estimates for all Virginia tracts for a given year."""
    api_key = CENSUS_API_KEY or os.getenv("CENSUS_API_KEY", "")
    if not api_key:
        raise ValueError("CENSUS_API_KEY is not set")

    variables = ",".join(ACS_VARIABLES.keys())
    url = (
        f"https://api.census.gov/data/{year}/acs/acs5"
        f"?get={variables}"
        f"&for=tract:*&in=state:{STATE_FIPS}"
        f"&key={api_key}"
    )

    print(f"Fetching ACS {year} data...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    headers = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=headers)

    # Build GEOID from state + county + tract
    df["geoid"] = df["state"] + df["county"] + df["tract"]

    # Convert numeric columns
    for var_code in ACS_VARIABLES:
        col = var_code
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def compute_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Compute percentage fields from raw ACS counts."""
    # % renters
    total_tenure = df["B25003_001E"]
    renter = df["B25003_003E"]
    df["pct_renters"] = (renter / total_tenure * 100).round(2)

    # % rent burdened (paying >30% of income on rent)
    rent_burden_total = df["B25070_001E"]
    rent_burdened = (
        df["B25070_007E"] + df["B25070_008E"] + df["B25070_009E"] + df["B25070_010E"]
    )
    df["pct_rent_burdened"] = (rent_burdened / rent_burden_total * 100).round(2)

    # % non-white
    race_total = df["B02001_001E"]
    white = df["B02001_002E"]
    df["pct_nonwhite"] = ((race_total - white) / race_total * 100).round(2)

    # % below poverty
    poverty_total = df["B17001_001E"]
    poverty_below = df["B17001_002E"]
    df["pct_below_poverty"] = (poverty_below / poverty_total * 100).round(2)

    # % with bachelor's degree or higher
    edu_total = df["B15003_001E"]
    bachelors_plus = (
        df["B15003_022E"] + df["B15003_023E"] + df["B15003_024E"] + df["B15003_025E"]
    )
    df["pct_bachelors_plus"] = (bachelors_plus / edu_total * 100).round(2)

    return df


def insert_acs_data(df: pd.DataFrame, year: int, engine):
    """Insert ACS data into tract_indicators table."""
    with engine.begin() as conn:
        # Delete existing ACS data for this year
        conn.execute(
            text("DELETE FROM tract_indicators WHERE source = 'acs' AND data_year = :year"),
            {"year": year},
        )

        count = 0
        for _, row in df.iterrows():
            geoid = row["geoid"]

            # Check if this tract exists in census_tracts
            exists = conn.execute(
                text("SELECT 1 FROM census_tracts WHERE geoid = :geoid"),
                {"geoid": geoid},
            ).fetchone()

            if not exists:
                continue

            conn.execute(
                text("""
                    INSERT INTO tract_indicators (
                        geoid, data_year, source,
                        median_rent, median_home_value, median_household_income,
                        pct_renters, pct_rent_burdened, pct_below_poverty,
                        pct_nonwhite, pct_bachelors_plus,
                        total_population, total_households
                    ) VALUES (
                        :geoid, :year, 'acs',
                        :median_rent, :median_home_value, :median_household_income,
                        :pct_renters, :pct_rent_burdened, :pct_below_poverty,
                        :pct_nonwhite, :pct_bachelors_plus,
                        :total_population, :total_households
                    )
                    ON CONFLICT (geoid, data_year, source) DO UPDATE SET
                        median_rent = :median_rent,
                        median_home_value = :median_home_value,
                        median_household_income = :median_household_income,
                        pct_renters = :pct_renters,
                        pct_rent_burdened = :pct_rent_burdened,
                        pct_below_poverty = :pct_below_poverty,
                        pct_nonwhite = :pct_nonwhite,
                        pct_bachelors_plus = :pct_bachelors_plus,
                        total_population = :total_population,
                        total_households = :total_households
                """),
                {
                    "geoid": geoid,
                    "year": year,
                    "median_rent": None if pd.isna(row.get("B25064_001E")) else float(row["B25064_001E"]),
                    "median_home_value": None if pd.isna(row.get("B25077_001E")) else float(row["B25077_001E"]),
                    "median_household_income": None if pd.isna(row.get("B19013_001E")) else float(row["B19013_001E"]),
                    "pct_renters": None if pd.isna(row.get("pct_renters")) else float(row["pct_renters"]),
                    "pct_rent_burdened": None if pd.isna(row.get("pct_rent_burdened")) else float(row["pct_rent_burdened"]),
                    "pct_below_poverty": None if pd.isna(row.get("pct_below_poverty")) else float(row["pct_below_poverty"]),
                    "pct_nonwhite": None if pd.isna(row.get("pct_nonwhite")) else float(row["pct_nonwhite"]),
                    "pct_bachelors_plus": None if pd.isna(row.get("pct_bachelors_plus")) else float(row["pct_bachelors_plus"]),
                    "total_population": None if pd.isna(row.get("B01003_001E")) else int(row["B01003_001E"]),
                    "total_households": None if pd.isna(row.get("B11001_001E")) else int(row["B11001_001E"]),
                },
            )
            count += 1

        print(f"  Inserted {count} tracts for ACS {year}")


def run():
    """Run ACS ingestion for all configured years."""
    engine = create_engine(DATABASE_URL)

    for year in ACS_YEARS:
        try:
            df = fetch_acs_year(year)
            df = compute_derived_fields(df)
            insert_acs_data(df, year, engine)
        except Exception as e:
            print(f"  ERROR for ACS {year}: {e}")

    # Verify
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT data_year, COUNT(*) FROM tract_indicators WHERE source='acs' GROUP BY data_year ORDER BY data_year")
        ).fetchall()
        print("\nACS data summary:")
        for year, count in result:
            print(f"  {year}: {count} tracts")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    run()
