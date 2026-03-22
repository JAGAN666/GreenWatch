"""Simulation endpoint — run what-if scenarios for green investments."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.scoring.simulation_engine import (
    Intervention,
    Mitigation,
    simulate,
)

router = APIRouter()


class InterventionInput(BaseModel):
    type: str
    lat: float
    lng: float
    scale_value: float
    scale_unit: str = ""
    parameters: dict | None = None


class MitigationInput(BaseModel):
    type: str
    target_geoids: list[str]
    parameters: dict | None = None


class SimulateRequest(BaseModel):
    interventions: list[InterventionInput]
    mitigations: list[MitigationInput] = []


class TractResult(BaseModel):
    geoid: str
    county_name: str = ""
    state_fips: str = ""
    current_drs: float
    predicted_drs: float
    delta_drs: float
    current_ebs: float
    predicted_ebs: float
    delta_ebs: float
    confidence_lower: float
    confidence_upper: float
    equity_warning: bool


class SimulateResponse(BaseModel):
    total_population_affected: int
    total_tracts_affected: int
    equity_warnings_count: int
    equity_score: float
    summary_text: str
    affected_tracts: list[TractResult]


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_scenario(request: SimulateRequest, db: Session = Depends(get_db)):
    """Run a what-if simulation with proposed interventions and mitigations."""

    # Convert Pydantic models to dataclasses
    interventions = [
        Intervention(
            type=i.type,
            lat=i.lat,
            lng=i.lng,
            scale_value=i.scale_value,
            scale_unit=i.scale_unit,
            parameters=i.parameters or {},
        )
        for i in request.interventions
    ]

    mitigations = [
        Mitigation(
            type=m.type,
            target_geoids=m.target_geoids,
            parameters=m.parameters or {},
        )
        for m in request.mitigations
    ]

    result = simulate(db, interventions, mitigations)

    return SimulateResponse(**result)
