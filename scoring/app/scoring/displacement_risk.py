"""Displacement Risk Score (DRS) computation engine.

Computes percentile-ranked vulnerability, market pressure, and green proximity
scores for all Virginia census tracts.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Domain weights (from pipeline/config.py)
WEIGHTS = {
    "vulnerability": 0.40,
    "market_pressure": 0.35,
    "green_proximity": 0.25,
}

# Vulnerability indicators (higher raw value = higher vulnerability)
VULNERABILITY_COLS = [
    "pct_renters",
    "pct_rent_burdened",
    "pct_below_poverty",
    "pct_nonwhite",
    "pct_bachelors_plus",  # will be inverted (lower education = higher vulnerability)
    "eviction_rate",
    "svi_overall",
]

# Market pressure indicators — computed as 5-year % change
MARKET_PRESSURE_COLS = [
    "median_rent",
    "median_home_value",
    "median_household_income",  # will be inverted (rising income = more pressure)
]


def _classify(score: float) -> str:
    if score < 25:
        return "low"
    elif score < 50:
        return "moderate"
    elif score < 75:
        return "high"
    else:
        return "critical"


def _percentile_rank(series: pd.Series) -> pd.Series:
    """Rank values as percentiles 0-100. NaN stays NaN."""
    return series.rank(pct=True, na_option="keep") * 100


def compute_all_scores(db: Session) -> dict[str, dict[str, Any]]:
    """Compute DRS for all tracts. Returns {geoid: {drs_composite, ...}}."""

    # ── 1. Load latest-year indicators for vulnerability ──
    latest_year_q = text("SELECT MAX(data_year) FROM tract_indicators WHERE source = 'acs'")
    result = db.execute(latest_year_q)
    latest_year = result.scalar()
    if latest_year is None:
        # Fallback: use max year across all sources
        latest_year = db.execute(text("SELECT MAX(data_year) FROM tract_indicators")).scalar()

    logger.info(f"DRS: using latest year {latest_year}")

    # Pull latest indicators
    cols = ", ".join([
        "geoid", "data_year", "pct_renters", "pct_rent_burdened", "pct_below_poverty",
        "pct_nonwhite", "pct_bachelors_plus", "eviction_rate", "svi_overall",
        "median_rent", "median_home_value", "median_household_income",
    ])
    q = text(f"""
        SELECT {cols}
        FROM tract_indicators
        WHERE data_year = :yr
        ORDER BY geoid
    """)
    rows = db.execute(q, {"yr": latest_year}).fetchall()
    if not rows:
        logger.warning("DRS: no indicator rows found")
        return {}

    df = pd.DataFrame(rows, columns=[
        "geoid", "data_year", "pct_renters", "pct_rent_burdened", "pct_below_poverty",
        "pct_nonwhite", "pct_bachelors_plus", "eviction_rate", "svi_overall",
        "median_rent", "median_home_value", "median_household_income",
    ])

    # De-duplicate: if multiple sources for same geoid/year, take the first non-null
    df = df.groupby("geoid", as_index=False).first()
    df = df.set_index("geoid")

    # ── 2. Vulnerability domain ──
    vuln = pd.DataFrame(index=df.index)
    for col in VULNERABILITY_COLS:
        if col == "pct_bachelors_plus":
            # Invert: lower education = higher vulnerability
            vuln[col] = 100 - _percentile_rank(df[col])
        else:
            vuln[col] = _percentile_rank(df[col])

    # Fill NaN with 50 (neutral percentile)
    vuln = vuln.fillna(50.0)
    vulnerability = vuln.mean(axis=1)

    # ── 3. Market Pressure domain (5-year % change) ──
    earliest_year_q = text("SELECT MIN(data_year) FROM tract_indicators WHERE source = 'acs'")
    result = db.execute(earliest_year_q)
    earliest_year = result.scalar()
    if earliest_year is None:
        earliest_year = db.execute(text("SELECT MIN(data_year) FROM tract_indicators")).scalar()

    logger.info(f"DRS market pressure: comparing {earliest_year} -> {latest_year}")

    market_cols_str = ", ".join(["geoid", "data_year"] + MARKET_PRESSURE_COLS)

    if earliest_year and earliest_year < latest_year:
        q_early = text(f"""
            SELECT {market_cols_str}
            FROM tract_indicators
            WHERE data_year = :yr
        """)
        q_late = text(f"""
            SELECT {market_cols_str}
            FROM tract_indicators
            WHERE data_year = :yr
        """)
        early_rows = db.execute(q_early, {"yr": earliest_year}).fetchall()
        late_rows = db.execute(q_late, {"yr": latest_year}).fetchall()

        cols_list = ["geoid", "data_year"] + MARKET_PRESSURE_COLS
        df_early = pd.DataFrame(early_rows, columns=cols_list).groupby("geoid", as_index=False).first().set_index("geoid")
        df_late = pd.DataFrame(late_rows, columns=cols_list).groupby("geoid", as_index=False).first().set_index("geoid")

        # Compute % change
        pct_change = pd.DataFrame(index=df.index)
        for col in MARKET_PRESSURE_COLS:
            early_vals = df_early[col].reindex(df.index)
            late_vals = df_late[col].reindex(df.index)
            # Avoid division by zero
            safe_early = early_vals.replace(0, np.nan)
            pct_change[col] = ((late_vals - early_vals) / safe_early.abs()) * 100

        # Percentile-rank the changes
        market = pd.DataFrame(index=df.index)
        for col in MARKET_PRESSURE_COLS:
            if col == "median_household_income":
                # Rising income in neighborhood = gentrification pressure
                market[col] = _percentile_rank(pct_change[col])
            else:
                market[col] = _percentile_rank(pct_change[col])

        market = market.fillna(50.0)
        market_pressure = market.mean(axis=1)
    else:
        # No time-series data — use neutral
        logger.warning("DRS: no multi-year data for market pressure, using neutral 50")
        market_pressure = pd.Series(50.0, index=df.index)

    # ── 4. Green Proximity domain ──
    # Default to 50 for all tracts (no green_investments data yet)
    green_proximity = pd.Series(50.0, index=df.index)

    # ── 5. Composite DRS ──
    drs_composite = (
        WEIGHTS["vulnerability"] * vulnerability
        + WEIGHTS["market_pressure"] * market_pressure
        + WEIGHTS["green_proximity"] * green_proximity
    )

    # Clamp to 0-100
    drs_composite = drs_composite.clip(0, 100)

    # ── 6. Build results ──
    results: dict[str, dict[str, Any]] = {}
    for geoid in df.index:
        composite = float(drs_composite[geoid])
        results[geoid] = {
            "drs_vulnerability": round(float(vulnerability[geoid]), 2),
            "drs_market_pressure": round(float(market_pressure[geoid]), 2),
            "drs_green_proximity": round(float(green_proximity[geoid]), 2),
            "drs_composite": round(composite, 2),
            "drs_classification": _classify(composite),
        }

    logger.info(f"DRS: computed scores for {len(results)} tracts")
    return results
