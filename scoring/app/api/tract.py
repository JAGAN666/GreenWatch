"""Tract detail endpoint — returns full scoring breakdown and time-series data."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()

STATE_NAMES = {
    "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas",
    "06": "California", "08": "Colorado", "09": "Connecticut", "10": "Delaware",
    "11": "District of Columbia", "12": "Florida", "13": "Georgia", "15": "Hawaii",
    "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa",
    "20": "Kansas", "21": "Kentucky", "22": "Louisiana", "23": "Maine",
    "24": "Maryland", "25": "Massachusetts", "26": "Michigan", "27": "Minnesota",
    "28": "Mississippi", "29": "Missouri", "30": "Montana", "31": "Nebraska",
    "32": "Nevada", "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico",
    "36": "New York", "37": "North Carolina", "38": "North Dakota", "39": "Ohio",
    "40": "Oklahoma", "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island",
    "45": "South Carolina", "46": "South Dakota", "47": "Tennessee", "48": "Texas",
    "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
    "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming",
    # Territories
    "60": "American Samoa", "66": "Guam", "69": "Northern Mariana Islands",
    "72": "Puerto Rico", "78": "U.S. Virgin Islands",
}


@router.get("/tract/{geoid}")
async def get_tract_scoring(geoid: str, db: Session = Depends(get_db)):
    """Return full detail for a single tract: scores, indicators, time-series."""

    # ── 1. Check tract exists ──
    tract = db.execute(
        text("SELECT geoid, county_name, state_fips FROM census_tracts WHERE geoid = :geoid"),
        {"geoid": geoid},
    ).fetchone()

    if not tract:
        raise HTTPException(status_code=404, detail=f"Tract {geoid} not found")

    state_fips = tract[2] or ""
    state_name = STATE_NAMES.get(state_fips, "")

    # ── 2. Get latest scores ──
    score_row = db.execute(
        text("""
            SELECT score_version, data_year,
                   drs_vulnerability, drs_market_pressure, drs_green_proximity,
                   drs_composite, drs_classification,
                   ebs_air_quality, ebs_green_infra, ebs_climate_resilience,
                   ebs_health, ebs_composite,
                   accelerating_risk
            FROM tract_scores
            WHERE geoid = :geoid
            ORDER BY score_version DESC
            LIMIT 1
        """),
        {"geoid": geoid},
    ).fetchone()

    scores = None
    if score_row:
        scores = {
            "score_version": score_row[0],
            "data_year": score_row[1],
            "displacement_risk": {
                "vulnerability": score_row[2],
                "market_pressure": score_row[3],
                "green_proximity": score_row[4],
                "composite": score_row[5],
                "classification": score_row[6],
            },
            "environmental_benefit": {
                "air_quality": score_row[7],
                "green_infra": score_row[8],
                "climate_resilience": score_row[9],
                "health": score_row[10],
                "composite": score_row[11],
            },
            "accelerating_risk": score_row[12],
        }

    # ── 3. Get latest indicators ──
    indicator_cols = [
        "data_year", "source",
        "median_rent", "median_home_value", "median_household_income",
        "pct_renters", "pct_rent_burdened", "pct_below_poverty",
        "pct_nonwhite", "pct_bachelors_plus", "total_population",
        "pm25", "ozone", "diesel_pm",
        "svi_overall", "nri_risk_score", "nri_flood_score",
        "nri_heat_score", "nri_hurricane_score",
        "asthma_prevalence", "mental_health_not_good",
        "eviction_rate", "cejst_disadvantaged",
        "tree_canopy_pct", "impervious_surface_pct",
        "park_access_10min", "flood_zone_pct",
    ]
    cols_str = ", ".join(indicator_cols)

    latest_row = db.execute(
        text(f"""
            SELECT {cols_str}
            FROM tract_indicators
            WHERE geoid = :geoid
            ORDER BY data_year DESC
            LIMIT 1
        """),
        {"geoid": geoid},
    ).fetchone()

    indicators = None
    if latest_row:
        indicators = {}
        for i, col in enumerate(indicator_cols):
            val = latest_row[i]
            indicators[col] = val

    # ── 4. Time-series data (all years) ──
    ts_rows = db.execute(
        text("""
            SELECT data_year, source,
                   median_rent, median_home_value, median_household_income,
                   pct_renters, pct_rent_burdened, pct_below_poverty, total_population
            FROM tract_indicators
            WHERE geoid = :geoid
            ORDER BY data_year ASC
        """),
        {"geoid": geoid},
    ).fetchall()

    time_series = []
    for row in ts_rows:
        time_series.append({
            "year": row[0],
            "source": row[1],
            "median_rent": row[2],
            "median_home_value": row[3],
            "median_household_income": row[4],
            "pct_renters": row[5],
            "pct_rent_burdened": row[6],
            "pct_below_poverty": row[7],
            "total_population": row[8],
        })

    return {
        "geoid": geoid,
        "county_name": tract[1] or "",
        "state_fips": state_fips,
        "state_name": state_name,
        "scores": scores,
        "indicators": indicators,
        "time_series": time_series,
    }
