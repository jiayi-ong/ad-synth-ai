import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.core.config import settings
from backend.core.logger import setup_logging
from backend.core.logging_middleware import ObservabilityMiddleware
from backend.db.base import Base, engine
from backend.routers import advertisements, auth, brands, campaigns, chatbot, evaluate, generation, personas, products, research

# Import all models so SQLAlchemy registers them before create_all
import backend.models  # noqa: F401

_startup_logger = logging.getLogger(__name__)

# (table, column, sqlite_type, pg_type) — covers all columns added after initial deployment
_COLUMN_MIGRATIONS: list[tuple[str, str, str, str]] = [
    ("products",       "unit_cost_usd",              "REAL",    "DOUBLE PRECISION"),
    ("campaigns",      "brand_profile_id",            "VARCHAR", "VARCHAR"),
    ("campaigns",      "target_channels",             "TEXT",    "TEXT"),
    ("campaigns",      "campaign_notes",              "TEXT",    "TEXT"),
    ("advertisements", "brand_profile_id",            "VARCHAR", "VARCHAR"),
    ("advertisements", "target_channel",              "VARCHAR", "VARCHAR"),
    ("advertisements", "evaluation_output",           "TEXT",    "TEXT"),
    ("advertisements", "channel_adaptation_output",   "TEXT",    "TEXT"),
    ("advertisements", "brand_consistency_score",     "REAL",    "DOUBLE PRECISION"),
    ("advertisements", "text_variants",               "TEXT",    "TEXT"),
    ("advertisements", "video_url",                   "VARCHAR", "VARCHAR"),
    ("advertisements", "pipeline_state_history",      "TEXT",    "TEXT"),
]


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
    # Create all tables (includes ChatSession added for chatbot feature)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialise chatbot knowledge base (embeddings loaded or generated at startup)
    from backend.services import knowledge_base as _kb
    try:
        _kb.initialise(embed_on_startup=settings.chatbot_embed_on_startup)
    except Exception as _kb_err:
        _startup_logger.warning("chatbot knowledge base init failed (chatbot will still work, KB search disabled): %s", _kb_err)

    # Inline schema migrations: add new columns to existing tables without Alembic
    is_sqlite = "sqlite" in settings.database_url
    async with engine.connect() as conn:
        for table, column, sqlite_type, pg_type in _COLUMN_MIGRATIONS:
            if is_sqlite:
                result = await conn.execute(text(f"PRAGMA table_info({table})"))
                existing_cols = {row[1] for row in result.fetchall()}
                missing = column not in existing_cols
            else:
                result = await conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name = '{table}' AND column_name = '{column}'"
                ))
                missing = result.fetchone() is None
            if missing:
                col_type = sqlite_type if is_sqlite else pg_type
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                await conn.commit()
                _startup_logger.info("schema_migration: added %s to %s", column, table)

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
app.include_router(chatbot.router)

# Serve frontend at /app (added after other routes to avoid catch-all conflicts)
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.get("/")
async def root():
    return RedirectResponse(url="/app")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
