from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env into os.environ before any google-genai/ADK imports, because those
# libraries read GOOGLE_API_KEY and GOOGLE_GENAI_USE_VERTEXAI directly from
# os.environ (pydantic-settings populates the Settings object but not os.environ).
load_dotenv(override=False)


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
    # Thinking budget for tool-using agents. 0 prevents MALFORMED_FUNCTION_CALL on 2.0-flash
    # but causes blank output on 2.5-flash (which needs some thinking to produce text after
    # tool calls). A small non-zero value works on both: 2.0-flash ignores ThinkingConfig,
    # 2.5-flash uses the budget and produces proper output. Set to 0 only if reverting to 2.0-flash.
    agent_thinking_budget: int = 1024

    # ── Image generation ─────────────────────────────────────────────────────
    image_gen_provider: Literal["vertexai", "gemini", "shortapi", "mock"] = "mock"
    imagen_model: str = "imagen-3.0-generate-002"
    gemini_image_model: str = "gemini-2.0-flash-exp-image-generation"
    shortapi_api_key: str = ""
    shortapi_model: str = "google/nano-banana-pro/text-to-image"
    shortapi_aspect_ratio: str = "4:5"

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

    # ── Observability ─────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "text"] = "json"
    log_dir: str = "logs"
    log_to_file: bool = True

    # ── Chatbot Assistant ─────────────────────────────────────────────────────
    chatbot_max_turns: int = 20
    chatbot_knowledge_threshold: float = 0.82
    chatbot_embed_on_startup: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
