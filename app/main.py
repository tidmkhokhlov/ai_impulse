from fastapi import FastAPI
from app.api.v1 import analyze, incidents
from app.core.config import settings
from app.services.fetch import fetch

app = FastAPI(title="AI Impulse - Audit API")

app.include_router(analyze.router, prefix="/api/v1/analyze", tags=["analyze"])
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])

@app.get("/")
async def root():
    return {"status": "ok", "service": "ai-impulse"}
