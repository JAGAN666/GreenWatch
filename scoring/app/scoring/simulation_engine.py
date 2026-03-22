"""What-if simulation engine for green investment scenarios.

Given a set of proposed interventions (parks, greenways, etc.) and optional
mitigations (rent stabilization, CLTs, etc.), computes predicted changes to
DRS and EBS for all affected census tracts.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Impact radii in meters
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

# Mitigation DRS reduction (points)
MITIGATION_EFFECTS = {
    "rent_stabilization": 20,
    "community_land_trust": 25,
    "affordable_housing": 15,
    "community_benefit_agreement": 10,
}


@dataclass
class Intervention:
    type: str
    lat: float
    lng: float
    scale_value: float
    scale_unit: str = ""
    parameters: dict = field(default_factory=dict)


@dataclass
class Mitigation:
    type: str
    target_geoids: list[str]
    parameters: dict = field(default_factory=dict)


@dataclass
class TractImpact:
    geoid: str
    county_name: str
    state_fips: str
    distance: float
    current_drs: float
    current_ebs: float
    delta_drs: float
    delta_ebs: float
    equity_warning: bool
    total_population: int


def simulate(
    db: Session,
    interventions: list[Intervention],
    mitigations: list[Mitigation] | None = None,
) -> dict[str, Any]:
    """Run a what-if simulation and return results."""

    if mitigations is None:
        mitigations = []

    # Accumulate impacts per tract
    tract_impacts: dict[str, TractImpact] = {}

    # ── Step 1 & 2: Find affected tracts and compute EBS/DRS deltas ──
    for intervention in interventions:
        itype = intervention.type
        radius = max(IMPACT_RADII.get(itype, 1000), 500)  # minimum 500m effective radius
        base_ebs = BASE_EBS_EFFECT.get(itype, 5)
        base_drs = BASE_DRS_EFFECT.get(itype, 3)
        scale_factor = min(intervention.scale_value / 10.0, 2.0)

        # PostGIS spatial query: find tracts within radius OR containing the point
        # Uses ST_Distance on geom (nearest boundary point) not centroid
        q = text("""
            SELECT
                ct.geoid,
                ct.county_name,
                ct.state_fips,
                ST_Distance(
                    ct.geom::geography,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                ) AS dist,
                COALESCE(ts.drs_composite, 50) AS current_drs,
                COALESCE(ts.ebs_composite, 50) AS current_ebs,
                COALESCE(ti.total_population, 0) AS total_population
            FROM census_tracts ct
            LEFT JOIN tract_scores ts ON ct.geoid = ts.geoid
            LEFT JOIN (
                SELECT DISTINCT ON (geoid) geoid, total_population
                FROM tract_indicators
                WHERE source = 'acs'
                ORDER BY geoid, data_year DESC
            ) ti ON ct.geoid = ti.geoid
            WHERE ST_DWithin(
                ct.geom::geography,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                :radius
            )
            OR ST_Contains(
                ct.geom,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
            )
            ORDER BY dist
        """)

        rows = db.execute(q, {
            "lng": intervention.lng,
            "lat": intervention.lat,
            "radius": radius,
        }).fetchall()

        logger.info(
            f"Intervention {itype} at ({intervention.lat}, {intervention.lng}): "
            f"{len(rows)} tracts within {radius}m"
        )

        for row in rows:
            geoid = row[0]
            county_name = row[1] or ""
            state_fips = row[2] or ""
            dist = float(row[3])
            current_drs = float(row[4])
            current_ebs = float(row[5])
            total_pop = int(row[6]) if row[6] else 0

            # Distance decay: full effect at 0, minimum 0.1 at radius edge
            # dist here is distance to nearest tract boundary (0 if point is inside)
            distance_decay = 1.0 - (dist / radius)
            distance_decay = max(distance_decay, 0.1)  # always at least 10% effect

            # EBS delta (always positive — environmental improvement)
            delta_ebs = base_ebs * distance_decay * scale_factor

            # DRS delta (displacement pressure)
            vulnerability_multiplier = current_drs / 50.0
            delta_drs = base_drs * vulnerability_multiplier * distance_decay * scale_factor

            if geoid in tract_impacts:
                # Accumulate from multiple interventions
                existing = tract_impacts[geoid]
                existing.delta_ebs += delta_ebs
                existing.delta_drs += delta_drs
            else:
                tract_impacts[geoid] = TractImpact(
                    geoid=geoid,
                    county_name=county_name,
                    state_fips=state_fips,
                    distance=dist,
                    current_drs=current_drs,
                    current_ebs=current_ebs,
                    delta_drs=delta_drs,
                    delta_ebs=delta_ebs,
                    equity_warning=False,
                    total_population=total_pop,
                )

    # ── Step 4: Apply mitigations ──
    mitigation_by_geoid: dict[str, float] = {}
    for mitigation in mitigations:
        reduction = MITIGATION_EFFECTS.get(mitigation.type, 10)
        for geoid in mitigation.target_geoids:
            mitigation_by_geoid[geoid] = mitigation_by_geoid.get(geoid, 0) + reduction

    for geoid, impact in tract_impacts.items():
        if geoid in mitigation_by_geoid:
            # Reduce DRS delta by mitigation amount (but don't go below 0)
            impact.delta_drs = max(0, impact.delta_drs - mitigation_by_geoid[geoid])

    # ── Step 5: Equity warnings ──
    equity_warnings_count = 0
    for impact in tract_impacts.values():
        if impact.current_drs > 50 and impact.delta_drs > 5:
            impact.equity_warning = True
            equity_warnings_count += 1

    # ── Step 6: Build summary ──
    total_population = sum(t.total_population for t in tract_impacts.values())
    total_tracts = len(tract_impacts)

    # Compute equity score: 100 = no equity concerns, lower = worse
    if total_tracts > 0:
        warning_ratio = equity_warnings_count / total_tracts
        equity_score = round((1.0 - warning_ratio) * 100, 1)
    else:
        equity_score = 100.0

    # Narrative summary
    intervention_types = [i.type.replace("_", " ") for i in interventions]
    intervention_summary = ", ".join(intervention_types)
    mitigation_types = [m.type.replace("_", " ") for m in mitigations]

    narrative_parts = [
        f"Simulated {len(interventions)} intervention(s) ({intervention_summary}) "
        f"affecting {total_tracts} census tract(s) and approximately "
        f"{total_population:,} residents."
    ]

    if equity_warnings_count > 0:
        narrative_parts.append(
            f"WARNING: {equity_warnings_count} tract(s) with existing high displacement "
            f"risk may experience significant additional pressure."
        )

    if mitigations:
        narrative_parts.append(
            f"Mitigations applied: {', '.join(mitigation_types)}."
        )

    summary_text = " ".join(narrative_parts)

    # Build affected tracts list
    affected_tracts = []
    for impact in sorted(tract_impacts.values(), key=lambda t: -t.delta_drs):
        predicted_drs = min(100, impact.current_drs + impact.delta_drs)
        predicted_ebs = min(100, impact.current_ebs + impact.delta_ebs)

        # Simple confidence interval: +/- 20% of delta
        drs_margin = impact.delta_drs * 0.2
        affected_tracts.append({
            "geoid": impact.geoid,
            "county_name": impact.county_name,
            "state_fips": impact.state_fips,
            "current_drs": round(impact.current_drs, 2),
            "predicted_drs": round(predicted_drs, 2),
            "delta_drs": round(impact.delta_drs, 2),
            "current_ebs": round(impact.current_ebs, 2),
            "predicted_ebs": round(predicted_ebs, 2),
            "delta_ebs": round(impact.delta_ebs, 2),
            "confidence_lower": round(predicted_drs - drs_margin, 2),
            "confidence_upper": round(predicted_drs + drs_margin, 2),
            "equity_warning": impact.equity_warning,
        })

    return {
        "total_population_affected": total_population,
        "total_tracts_affected": total_tracts,
        "equity_warnings_count": equity_warnings_count,
        "equity_score": equity_score,
        "summary_text": summary_text,
        "affected_tracts": affected_tracts,
    }
