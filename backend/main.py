from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.core.config import settings
from backend.db.base import Base, engine
from backend.routers import advertisements, auth, campaigns, generation, personas, products

# Import all models so SQLAlchemy registers them before create_all
import backend.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Ad-Synth-AI", version="0.1.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(campaigns.router)
app.include_router(products.router)
app.include_router(personas.router)
app.include_router(advertisements.router)
app.include_router(generation.router)

# Serve frontend at /app (added after other routes to avoid catch-all conflicts)
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
