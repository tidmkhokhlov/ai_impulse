from fastapi import FastAPI
from app.api.v1 import analyze, incidents
from app.db.init_db import init_db

app = FastAPI(title="AI Impulse - Audit API")

app.include_router(analyze.router, prefix="/api/v1/analyze", tags=["analyze"])
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])

@app.get("/")
async def root():
    return {"status": "ok", "service": "ai-impulse"}

# ====== Инициализация БД при старте ======
@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
    except Exception as e:
        print(f"⚠️ Ошибка инициализации базы: {e}")
