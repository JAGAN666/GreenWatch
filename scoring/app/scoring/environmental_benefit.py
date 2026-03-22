"""Environmental Benefit Score (EBS) computation engine.

Computes percentile-ranked air quality, green infrastructure, climate resilience,
and health domain scores for all Virginia census tracts.
"""

import logging
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Domain weights (from pipeline/config.py)
WEIGHTS = {
    "air_quality": 0.30,
    "green_infra": 0.30,
    "climate_resilience": 0.25,
    "health": 0.15,
}

# Indicators per domain, with inversion flag
# True = INVERT (lower raw value = better = higher score)
DOMAINS = {
    "air_quality": [
        ("pm25", True),
        ("ozone", True),
        ("diesel_pm", True),
    ],
    "green_infra": [
        ("tree_canopy_pct", False),       # higher = better
        ("park_access_10min", False),      # boolean, handled specially
        ("impervious_surface_pct", True),  # lower = better
    ],
    "climate_resilience": [
        ("nri_flood_score", True),
        ("nri_heat_score", True),
        ("nri_hurricane_score", True),
    ],
    "health": [
        ("asthma_prevalence", True),
        ("mental_health_not_good", True),
    ],
}


def _percentile_rank(series: pd.Series) -> pd.Series:
    """Rank values as percentiles 0-100. NaN stays NaN."""
    return series.rank(pct=True, na_option="keep") * 100


def compute_all_scores(db: Session) -> dict[str, dict[str, Any]]:
    """Compute EBS for all tracts. Returns {geoid: {ebs_composite, ...}}."""

    # Find latest year
    latest_year = db.execute(text("SELECT MAX(data_year) FROM tract_indicators")).scalar()
    if latest_year is None:
        logger.warning("EBS: no data in tract_indicators")
        return {}

    logger.info(f"EBS: using latest year {latest_year}")

    # Collect all needed columns
    all_cols = set()
    for domain_indicators in DOMAINS.values():
        for col, _ in domain_indicators:
            all_cols.add(col)

    cols_str = ", ".join(["geoid"] + sorted(all_cols))
    q = text(f"""
        SELECT {cols_str}
        FROM tract_indicators
        WHERE data_year = :yr
        ORDER BY geoid
    """)
    rows = db.execute(q, {"yr": latest_year}).fetchall()
    if not rows:
        logger.warning("EBS: no rows found")
        return {}

    col_names = ["geoid"] + sorted(all_cols)
    df = pd.DataFrame(rows, columns=col_names)

    # De-duplicate: if multiple sources for same geoid/year, take first non-null
    df = df.groupby("geoid", as_index=False).first()
    df = df.set_index("geoid")

    # Compute domain scores
    domain_scores: dict[str, pd.Series] = {}

    for domain_name, indicators in DOMAINS.items():
        domain_df = pd.DataFrame(index=df.index)

        for col, invert in indicators:
            if col == "park_access_10min":
                # Boolean -> 100 (has access) or 0 (no access)
                raw = df[col].astype(float).fillna(0) * 100
                domain_df[col] = raw
            elif invert:
                # Lower raw = better -> higher score
                ranked = _percentile_rank(df[col])
                domain_df[col] = 100 - ranked
            else:
                domain_df[col] = _percentile_rank(df[col])

        # Fill NaN with 50 (neutral)
        domain_df = domain_df.fillna(50.0)
        domain_scores[domain_name] = domain_df.mean(axis=1)

    # Composite EBS
    ebs_composite = sum(
        WEIGHTS[domain] * domain_scores[domain]
        for domain in WEIGHTS
    )
    ebs_composite = ebs_composite.clip(0, 100)

    # Build results
    results: dict[str, dict[str, Any]] = {}
    for geoid in df.index:
        composite = float(ebs_composite[geoid])
        results[geoid] = {
            "ebs_air_quality": round(float(domain_scores["air_quality"][geoid]), 2),
            "ebs_green_infra": round(float(domain_scores["green_infra"][geoid]), 2),
            "ebs_climate_resilience": round(float(domain_scores["climate_resilience"][geoid]), 2),
            "ebs_health": round(float(domain_scores["health"][geoid]), 2),
            "ebs_composite": round(composite, 2),
        }

    logger.info(f"EBS: computed scores for {len(results)} tracts")
    return results
