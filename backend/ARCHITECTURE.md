# Backend Architecture

The backend is a FastAPI application that exposes a REST + SSE API, manages persistence, and drives the multi-agent pipeline.

## Directory Layout

```
backend/
├── main.py             # App factory: mounts routers, middleware, static files, lifespan
├── core/
│   ├── config.py       # Pydantic Settings — all config sourced from env vars / .env
│   ├── security.py     # JWT creation and verification (python-jose + bcrypt)
│   ├── dependencies.py # FastAPI Depends: get_current_user, get_db
│   ├── exceptions.py   # Custom HTTP exception handlers
│   └── logging_middleware.py  # Request/response logging, latency headers
├── db/
│   ├── base.py         # SQLAlchemy declarative Base, async engine factory
│   └── session.py      # AsyncSession factory (get_db dependency)
├── models/             # SQLAlchemy ORM models
│   ├── user.py
│   ├── campaign.py
│   ├── product.py
│   ├── persona.py
│   ├── advertisement.py
│   ├── brand_profile.py
│   └── research_cache.py
├── schemas/            # Pydantic v2 schemas for request/response validation
│   ├── auth.py
│   ├── brand_profile.py
│   ├── campaign.py
│   ├── product.py
│   ├── persona.py
│   ├── advertisement.py
│   ├── research.py
│   └── evaluate.py
├── routers/            # FastAPI APIRouter — one file per domain
│   ├── auth.py         # POST /auth/register, POST /auth/login
│   ├── brands.py       # CRUD /brands
│   ├── campaigns.py    # CRUD /campaigns
│   ├── products.py     # CRUD /products
│   ├── personas.py     # CRUD /personas
│   ├── advertisements.py  # CRUD /advertisements
│   ├── generation.py   # POST /generate (SSE streaming), POST /generate/ab-variant
│   ├── evaluate.py     # POST /evaluate
│   └── research.py     # GET /research (cached trend data)
├── services/           # Business logic decoupled from HTTP layer
│   ├── auth_service.py
│   ├── brand_service.py
│   ├── campaign_service.py
│   ├── product_service.py
│   ├── persona_service.py
│   ├── advertisement_service.py
│   └── image_service.py       # Multi-provider image generation factory
└── pipeline/           # Agent pipeline (see pipeline/ARCHITECTURE.md)
```

## Request Flow

```
HTTP Request
    │
    ▼
logging_middleware.py   ← attaches request_id, logs method/path/latency
    │
    ▼
Router (FastAPI)
    │
    ├── Depends(get_current_user)  ← validates JWT, fetches User from DB
    ├── Depends(get_db)            ← yields AsyncSession
    │
    ▼
Service layer          ← all DB queries, business rules
    │
    ▼
HTTP Response / SSE Stream
```

## Configuration (`core/config.py`)

All configuration is read from environment variables (or a `.env` file) via `pydantic-settings`. The `Settings` class is instantiated once with `@lru_cache` and re-used everywhere via `get_settings()`.

**Config categories:**

| Category | Key Fields |
|----------|-----------|
| LLM | `google_api_key`, `google_genai_use_vertexai`, `gcp_project_id`, `gemini_model` |
| Image Gen | `image_gen_provider`, `imagen_model`, `gemini_image_model`, `shortapi_api_key`, `shortapi_model` |
| Trend Research | `google_cse_api_key`, `youtube_api_key`, `twitter_bearer_token`, `serpapi_api_key`, `reddit_*` |
| Auth | `jwt_secret_key`, `jwt_algorithm`, `jwt_expire_hours` |
| Database | `database_url`, `adk_database_url` |
| Storage | `storage_backend`, `gcs_bucket`, `upload_dir` |
| Observability | `log_level`, `log_format` |

## Authentication

JWT-based stateless auth:
1. `POST /auth/register` — hashes password with bcrypt, creates User record
2. `POST /auth/login` — verifies password, returns signed JWT
3. All protected routes use `Depends(get_current_user)` which decodes the JWT and returns the `User` ORM instance

## Data Models

All models use `SQLAlchemy` async ORM with `aiosqlite` (local) or Cloud SQL (production).

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `User` | id, email, hashed_password | owns Campaigns, Products, Personas |
| `BrandProfile` | id, name, company, mission, values, tone_keywords, brand_guidelines | owned by User; linked from Campaign |
| `Campaign` | id, name, mission, brand_profile_id | belongs to User; has Advertisements |
| `Product` | id, name, description, image_path | belongs to User |
| `Persona` | id, name, traits (JSON) | belongs to User; many-to-many with Advertisement |
| `Advertisement` | id, status, pipeline_state (JSON), image_url, ab_variant_url, image_gen_prompt, ab_variant_prompt | belongs to Campaign + Product |
| `ResearchCache` | id, query, embedding, result | sqlite-vec backed for RAG |

## Image Generation (`services/image_service.py`)

Pluggable provider pattern using an abstract base class:

```
ImageGenProvider (ABC)
├── MockImageGenProvider       IMAGE_GEN_PROVIDER=mock     (placeholder URL, no API calls)
├── VertexAIImagenProvider     IMAGE_GEN_PROVIDER=vertexai (Vertex AI Imagen 3)
├── GeminiImageProvider        IMAGE_GEN_PROVIDER=gemini   (Gemini generate_content API, dual-mode)
└── ShortAPIProvider           IMAGE_GEN_PROVIDER=shortapi (ShortAPI.io — Flux/DALL-E/SD)

create_image_provider() → factory that reads settings.image_gen_provider
create_video_provider() → MockVideoGenProvider (scaffold for future video support)
```

`GeminiImageProvider` supports both local dev (uses `GOOGLE_API_KEY`) and Cloud Run (uses Vertex AI credentials) via the `google_genai_use_vertexai` flag.

## Generation Endpoint (`routers/generation.py`)

The `POST /generate` endpoint is the core of the application. It:

1. Creates an `Advertisement` record with status `running`
2. Loads product, campaign, brand profile, and persona context
3. Builds pipeline input state (product description, marketing brief, brand context)
4. Starts the ADK `Runner.run_async()` and iterates over events as an async generator
5. For each agent `final_response` event — emits an SSE `agent_complete` event with the agent's JSON output
6. On pipeline completion — calls `create_image_provider().generate()` for primary and A/B variant images
7. Saves full `pipeline_state` to the Advertisement record

**Agent → State Key mapping** (`_AGENT_KEY_MAP`):

| Agent | State Key Written |
|-------|------------------|
| `product_understanding_agent` | `product_profile` |
| `audience_positioning_agent` | `audience_analysis` |
| `trend_critic_agent` | `trend_research` |
| `competitor_agent` | `competitor_analysis` |
| `creative_strategy_agent` | `creative_directions` |
| `persona_agent` | `selected_persona` |
| `prompt_engineering_agent` | `image_gen_prompt` |
| `marketing_recommendation_agent` | `marketing_output` |
| `evaluation_agent` | `evaluation_output` |
| `channel_adaptation_agent` | `channel_adaptation` |
| `brand_consistency_agent` | `brand_consistency` |

Non-critical agents (failures don't halt the pipeline): `trend_critic_agent`, `competitor_agent`, `marketing_recommendation_agent`, `evaluation_agent`, `channel_adaptation_agent`, `brand_consistency_agent`.

## SSE Event Protocol

All events are `data: <json>\n\n` formatted. Event types:

| Event | Payload |
|-------|---------|
| `started` | `{ advertisement_id }` |
| `agent_complete` | `{ agent, output, elapsed_ms }` |
| `image_generating` | `{ provider }` |
| `image_ready` | `{ url, ab_variant_url }` |
| `cost_estimate` | `{ input_tokens, output_tokens, cost_usd }` |
| `done` | `{ advertisement_id, elapsed_ms }` |
| `error` | `{ message }` |

## Deployment

- **Local**: `uv run uvicorn backend.main:app --reload --port 8000`
- **Docker**: Multi-stage build in `Dockerfile` — builder installs deps with uv, final image copies venv + code
- **Cloud Run**: `cloudbuild.yaml` builds image → pushes to GCR → deploys to Cloud Run (2 vCPU, 2 GB, 600s timeout)
