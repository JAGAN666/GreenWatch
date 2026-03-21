from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import simulate, recompute, tract

app = FastAPI(
    title="GreenWatch Scoring Engine",
    description="Displacement risk and environmental benefit scoring for Virginia census tracts",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulate.router, prefix="/scoring")
app.include_router(recompute.router, prefix="/scoring")
app.include_router(tract.router, prefix="/scoring")


@app.get("/scoring/health")
async def health_check():
    return {"status": "healthy", "service": "greenwatch-scoring"}
