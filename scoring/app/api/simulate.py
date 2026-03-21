from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


class InterventionInput(BaseModel):
    type: str
    lat: float
    lng: float
    scale_value: float
    scale_unit: str
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
    # TODO: Implement simulation engine in Phase 2
    return SimulateResponse(
        total_population_affected=0,
        total_tracts_affected=0,
        equity_warnings_count=0,
        equity_score=0.0,
        summary_text="Simulation engine not yet implemented.",
        affected_tracts=[],
    )
