from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


@router.post("/recompute")
async def recompute_scores(db: Session = Depends(get_db)):
    # TODO: Implement score recomputation in Phase 2
    return {"status": "not_implemented", "message": "Score recomputation not yet implemented."}
