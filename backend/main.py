import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.core.config import settings
from backend.core.logger import setup_logging
from backend.core.logging_middleware import ObservabilityMiddleware
from backend.db.base import Base, engine
from backend.routers import advertisements, auth, brands, campaigns, evaluate, generation, personas, products, research

# Import all models so SQLAlchemy registers them before create_all
import backend.models  # noqa: F401

_startup_logger = logging.getLogger(__name__)


def _asyncio_exception_handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """
    Suppress a known google-genai library bug where BaseApiClient.__del__ tries
    to call aclose() on a partially-initialised object that never had
    _http_options assigned (raised during garbage collection as an unretrieved
    background task).  All other exceptions are forwarded to the default handler.
    """
    exc = context.get("exception")
    if isinstance(exc, AttributeError) and "_http_options" in str(exc):
        _startup_logger.debug(
            "Suppressed known google-genai GC cleanup noise: %s", exc
        )
        return
    loop.default_exception_handler(context)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings)
    asyncio.get_event_loop().set_exception_handler(_asyncio_exception_handler)
    # Ensure data and log directories exist
    Path("data").mkdir(exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    Path(settings.log_dir).mkdir(exist_ok=True)
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Ad-Synth-AI", version="0.1.0", lifespan=lifespan)
app.add_middleware(ObservabilityMiddleware)

app.include_router(auth.router)
app.include_router(brands.router)
app.include_router(campaigns.router)
app.include_router(products.router)
app.include_router(products.all_router)
app.include_router(personas.router)
app.include_router(personas.all_router)
app.include_router(advertisements.router)
app.include_router(generation.router)
app.include_router(evaluate.router)
app.include_router(research.router)

# Serve frontend at /app (added after other routes to avoid catch-all conflicts)
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
