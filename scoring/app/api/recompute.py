"""Recompute all DRS and EBS scores and write to tract_scores table."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.scoring.displacement_risk import compute_all_scores as compute_drs
from app.scoring.environmental_benefit import compute_all_scores as compute_ebs

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/recompute")
async def recompute_scores(db: Session = Depends(get_db)):
    """Recompute DRS and EBS for all tracts and persist to tract_scores."""

    # Compute scores
    logger.info("Starting DRS computation...")
    drs_results = compute_drs(db)
    logger.info(f"DRS computed for {len(drs_results)} tracts")

    logger.info("Starting EBS computation...")
    ebs_results = compute_ebs(db)
    logger.info(f"EBS computed for {len(ebs_results)} tracts")

    # Get latest data year
    latest_year = db.execute(text("SELECT MAX(data_year) FROM tract_indicators")).scalar() or 2023
    score_version = f"v1_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # Merge and write to tract_scores
    all_geoids = set(drs_results.keys()) | set(ebs_results.keys())

    # Clear previous scores for this version prefix
    db.execute(text("DELETE FROM tract_scores WHERE score_version LIKE 'v1_%'"))

    count = 0
    for geoid in all_geoids:
        drs = drs_results.get(geoid, {})
        ebs = ebs_results.get(geoid, {})

        drs_composite = drs.get("drs_composite", 50.0)
        ebs_composite = ebs.get("ebs_composite", 50.0)

        # Accelerating risk: high displacement risk AND low environmental benefit
        accelerating_risk = drs_composite > 60 and ebs_composite < 40

        db.execute(text("""
            INSERT INTO tract_scores (
                geoid, score_version, data_year,
                drs_vulnerability, drs_market_pressure, drs_green_proximity,
                drs_composite, drs_classification,
                ebs_air_quality, ebs_green_infra, ebs_climate_resilience,
                ebs_health, ebs_composite,
                accelerating_risk
            ) VALUES (
                :geoid, :score_version, :data_year,
                :drs_vulnerability, :drs_market_pressure, :drs_green_proximity,
                :drs_composite, :drs_classification,
                :ebs_air_quality, :ebs_green_infra, :ebs_climate_resilience,
                :ebs_health, :ebs_composite,
                :accelerating_risk
            )
        """), {
            "geoid": geoid,
            "score_version": score_version,
            "data_year": latest_year,
            "drs_vulnerability": drs.get("drs_vulnerability", 50.0),
            "drs_market_pressure": drs.get("drs_market_pressure", 50.0),
            "drs_green_proximity": drs.get("drs_green_proximity", 50.0),
            "drs_composite": drs_composite,
            "drs_classification": drs.get("drs_classification", "moderate"),
            "ebs_air_quality": ebs.get("ebs_air_quality", 50.0),
            "ebs_green_infra": ebs.get("ebs_green_infra", 50.0),
            "ebs_climate_resilience": ebs.get("ebs_climate_resilience", 50.0),
            "ebs_health": ebs.get("ebs_health", 50.0),
            "ebs_composite": ebs_composite,
            "accelerating_risk": accelerating_risk,
        })
        count += 1

    db.commit()
    logger.info(f"Wrote {count} tract scores (version: {score_version})")

    return {
        "status": "success",
        "tracts_scored": count,
        "score_version": score_version,
        "data_year": latest_year,
    }
