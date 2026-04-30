from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    google_genai_use_vertexai: bool = False
    google_api_key: str = ""           # AI Studio key for local dev
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    gemini_model: str = "gemini-2.0-flash"

    # ── Image generation ─────────────────────────────────────────────────────
    image_gen_provider: Literal["vertexai", "mock"] = "mock"
    imagen_model: str = "imagen-3.0-generate-002"

    # ── Search / Trend Research ───────────────────────────────────────────────
    google_cse_api_key: str = ""
    google_cse_id: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "ad-synth-ai/0.1"
    youtube_api_key: str = ""
    twitter_bearer_token: str = ""
    serpapi_api_key: str = ""

    # ── Auth ──────────────────────────────────────────────────────────────────
    jwt_secret_key: str = "dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/ad_synth.db"
    adk_database_url: str = "sqlite+aiosqlite:///./data/adk_sessions.db"

    # ── Storage ───────────────────────────────────────────────────────────────
    storage_backend: Literal["local", "gcs"] = "local"
    gcs_bucket: str = ""
    upload_dir: Path = Path("data/uploads")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
