"""Optimize endpoint — find optimal locations for green interventions."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()

# Impact radii in meters (mirrors simulation_engine.py)
IMPACT_RADII = {
    "park": 1500,
    "greenway": 1000,
    "transit_stop": 800,
    "tree_planting": 500,
    "flood_infrastructure": 2000,
    "green_roof": 300,
}

# Base EBS improvement by intervention type (points)
BASE_EBS_EFFECT = {
    "park": 10,
    "greenway": 7,
    "transit_stop": 5,
    "tree_planting": 6,
    "flood_infrastructure": 8,
    "green_roof": 4,
}

# Base DRS increase (displacement pressure) by intervention type (points)
BASE_DRS_EFFECT = {
    "park": 8,
    "greenway": 5,
    "transit_stop": 10,
    "tree_planting": 3,
    "flood_infrastructure": 2,
    "green_roof": 2,
}


class OptimizeRequest(BaseModel):
    type: str  # intervention type
    scale_value: float
    scale_unit: str = ""
    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float


class OptimalLocation(BaseModel):
    lat: float
    lng: float
    geoid: str
    county_name: str
    state_fips: str
    optimization_score: float
    predicted_drs_delta: float
    predicted_ebs_delta: float
    current_drs: float
    current_ebs: float
    population: int
    reasoning: str  # human-readable explanation


class OptimizeResponse(BaseModel):
    optimal_locations: list[OptimalLocation]
    summary: str


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_location(request: OptimizeRequest, db: Session = Depends(get_db)):
    """Find the optimal location for a green intervention within a bounding box."""

    intervention_type = request.type.lower()
    if intervention_type not in BASE_EBS_EFFECT:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown intervention type '{request.type}'. "
                   f"Valid types: {', '.join(BASE_EBS_EFFECT.keys())}",
        )

    # Scale factor based on scale_value (normalize around 1.0 for a "standard" size)
    scale_factor = max(0.1, min(request.scale_value / 10.0, 5.0))

    # Query all tracts within the bounding box
    rows = db.execute(
        text("""
            SELECT ct.geoid,
                   ST_X(ct.centroid) AS lng,
                   ST_Y(ct.centroid) AS lat,
                   ct.county_name,
                   ct.state_fips,
                   ts.drs_composite,
                   ts.ebs_composite,
                   COALESCE(ti.total_population, 0) AS total_population
            FROM census_tracts ct
            JOIN tract_scores ts ON ct.geoid = ts.geoid
            LEFT JOIN LATERAL (
                SELECT total_population
                FROM tract_indicators
                WHERE geoid = ct.geoid
                ORDER BY data_year DESC
                LIMIT 1
            ) ti ON true
            WHERE ST_Intersects(
                ct.geom,
                ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
            )
        """),
        {
            "min_lng": request.min_lng,
            "min_lat": request.min_lat,
            "max_lng": request.max_lng,
            "max_lat": request.max_lat,
        },
    ).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No census tracts found within the specified bounding box.",
        )

    # Score each candidate tract
    base_ebs = BASE_EBS_EFFECT[intervention_type]
    base_drs = BASE_DRS_EFFECT[intervention_type]

    candidates = []
    for row in rows:
        geoid = row[0]
        lng = row[1]
        lat = row[2]
        county_name = row[3] or ""
        state_fips = row[4] or ""
        current_drs = float(row[5]) if row[5] is not None else 50.0
        current_ebs = float(row[6]) if row[6] is not None else 50.0
        population = int(row[7]) if row[7] is not None else 0

        # EBS potential: tracts with low EBS benefit most
        ebs_potential = 100.0 - current_ebs

        # DRS risk penalty: penalize placing in high-displacement areas
        drs_risk_penalty = current_drs * 0.5

        # Optimization score
        optimization_score = ebs_potential - drs_risk_penalty

        # Predicted deltas (scaled)
        predicted_ebs_delta = base_ebs * scale_factor * (ebs_potential / 100.0)
        predicted_drs_delta = base_drs * scale_factor * (current_drs / 100.0)

        candidates.append({
            "lat": lat,
            "lng": lng,
            "geoid": geoid,
            "county_name": county_name,
            "state_fips": state_fips,
            "optimization_score": round(optimization_score, 2),
            "predicted_drs_delta": round(predicted_drs_delta, 2),
            "predicted_ebs_delta": round(predicted_ebs_delta, 2),
            "current_drs": round(current_drs, 2),
            "current_ebs": round(current_ebs, 2),
            "population": population,
        })

    # Sort by optimization_score descending, take top 3
    candidates.sort(key=lambda c: c["optimization_score"], reverse=True)
    top_3 = candidates[:3]

    # Add reasoning to each
    for loc in top_3:
        loc["reasoning"] = (
            f"Tract {loc['geoid']} in {loc['county_name']} has low environmental benefit "
            f"(EBS={loc['current_ebs']}) and low displacement risk (DRS={loc['current_drs']}), "
            f"making it ideal for a {intervention_type}. "
            f"Predicted EBS gain: +{loc['predicted_ebs_delta']}, "
            f"DRS increase: +{loc['predicted_drs_delta']}."
        )

    optimal_locations = [OptimalLocation(**loc) for loc in top_3]

    summary = (
        f"Analyzed {len(candidates)} tracts in the viewport. "
        f"Top location: tract {top_3[0]['geoid']} in {top_3[0]['county_name']} "
        f"with optimization score {top_3[0]['optimization_score']}. "
        f"A {intervention_type} ({request.scale_value} {request.scale_unit}) here would "
        f"boost environmental benefit by +{top_3[0]['predicted_ebs_delta']} points "
        f"with only +{top_3[0]['predicted_drs_delta']} displacement risk increase."
    )

    return OptimizeResponse(optimal_locations=optimal_locations, summary=summary)
