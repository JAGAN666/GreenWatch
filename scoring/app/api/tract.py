from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


@router.get("/tract/{geoid}")
async def get_tract_scoring(geoid: str, db: Session = Depends(get_db)):
    # TODO: Implement tract detail scoring in Phase 2
    return {
        "geoid": geoid,
        "status": "not_implemented",
        "message": "Tract scoring detail not yet implemented.",
    }
