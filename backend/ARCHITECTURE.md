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
│   ├── product.py          # Includes unit_cost_usd (Float, nullable)
│   ├── persona.py
│   ├── advertisement.py
│   ├── brand_profile.py
│   └── research_cache.py
├── schemas/            # Pydantic v2 schemas for request/response validation
│   ├── auth.py
│   ├── brand_profile.py
│   ├── campaign.py
│   ├── product.py          # ProductCreate/Update/Read include unit_cost_usd
│   ├── persona.py
│   ├── advertisement.py
│   ├── research.py
│   └── evaluate.py
├── routers/            # FastAPI APIRouter — one file per domain
│   ├── auth.py         # POST /auth/register, POST /auth/login
│   ├── brands.py       # CRUD /brands
│   ├── campaigns.py    # CRUD /campaigns
│   ├── products.py     # CRUD /products (+ unit_cost_usd field)
│   ├── personas.py     # CRUD /personas
│   ├── advertisements.py  # CRUD /advertisements
│   ├── generation.py   # POST /generate (SSE), rerun-stage, retry-image, cancel, ab-variant
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

All models use SQLAlchemy async ORM with `aiosqlite` (local) or Cloud SQL (production).

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `User` | id, email, hashed_password | owns Campaigns, Products, Personas |
| `BrandProfile` | id, name, company, mission, values, tone_keywords, brand_guidelines | owned by User; linked from Campaign |
| `Campaign` | id, name, mission, brand_profile_id | belongs to User; has Advertisements |
| `Product` | id, name, description, image_path, **unit_cost_usd** | belongs to User |
| `Persona` | id, name, traits (JSON) | belongs to User; many-to-many with Advertisement |
| `Advertisement` | id, status, pipeline_state (JSON), image_url, ab_variant_url, image_gen_prompt, ab_variant_prompt | belongs to Campaign + Product |
| `ResearchCache` | id, query, embedding, result | sqlite-vec backed for RAG |

`unit_cost_usd` is a nullable Float on `Product`. It is appended to `RAW_PRODUCT_DESCRIPTION` as `"Unit Cost (per unit): $X.XX"` before the pipeline starts so the product agent can extract it. An inline SQLite schema migration in `main.py`'s lifespan handler adds the column to existing databases without Alembic.

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

`GeminiImageProvider` supports both local dev (`GOOGLE_API_KEY`) and Cloud Run (Vertex AI credentials) via the `google_genai_use_vertexai` flag.

## Generation Endpoint (`routers/generation.py`)

The `POST /generate` endpoint is the core of the application. It:

1. Validates product exists and has a description
2. Creates an `Advertisement` record with status `running`
3. Loads product (including `unit_cost_usd`), campaign, brand profile, and persona context
4. Builds pipeline `initial_state` with input keys **and pre-seeded optional keys** (`LOOP_FEEDBACK`, `MARKET_SEGMENTATION`, `PRICING_ANALYSIS`, `CAMPAIGN_ARCHITECTURE`)
5. Starts `Runner.run_async()` and iterates over events
6. For each agent `is_final_response()` event — reads output from `event.actions.state_delta` (preferred for loop agents) then `event.content`, then `session_service.get_session()` as fallback
7. Emits SSE `agent_complete` event; increments progress only on **first** completion of each state key (prevents loop iteration double-counting)
8. On pipeline completion — runs pricing fallback if `pricing_analysis` is absent; runs experiment_design fallback if `experiment_design` is absent; then calls image provider
9. Saves full `pipeline_state` to the Advertisement record

**Agent → State Key mapping** (`_AGENT_KEY_MAP`):

| Agent | State Key |
|-------|----------|
| `product_understanding_agent` | `product_profile` |
| `market_segmentation_agent` | `market_segmentation` |
| `audience_positioning_agent` | `audience_analysis` |
| `loop_evaluator_agent` | `loop_eval_signal` (internal, no UI tab) |
| `trend_validator_agent` | `trend_research` |
| `competitor_agent` | `competitor_analysis` |
| `pricing_analysis_agent` | `pricing_analysis` |
| `creative_strategy_agent` | `creative_directions` |
| `persona_agent` | `selected_persona` |
| `prompt_engineering_agent` | `image_gen_prompt` |
| `campaign_architecture_agent` | `campaign_architecture` |
| `experiment_design_agent` | `experiment_design` |
| `marketing_recommendation_agent` | `marketing_output` |
| `evaluation_agent` | `evaluation_output` |
| `channel_adaptation_agent` | `channel_adaptation` |
| `brand_consistency_agent` | `brand_consistency` |

**Non-critical agents** (failures don't halt the pipeline): `trend_validator_agent`, `competitor_agent`, `pricing_analysis_agent`, `campaign_architecture_agent`, `experiment_design_agent`, `marketing_recommendation_agent`, `evaluation_agent`, `channel_adaptation_agent`, `brand_consistency_agent`.

`_TOTAL_AGENTS = 16` (15 state-key-tracked agents + image generation).

**Post-pipeline fallbacks**: After the pipeline completes and before image generation, `generation.py` injects deterministic fallback output for any critical agents that produced no output:
- **Pricing fallback** — `compute_pricing_fallback()` from `pricing_analysis_agent.py`: cost-plus model at 2×/3×/5× multipliers anchored on `unit_cost_usd` from `PRODUCT_PROFILE`.
- **Experiment design fallback** — `compute_experiment_design_fallback()` from `experiment_design_agent.py`: 3 concrete A/B experiments (hook copy, CTA text, audience targeting) with scipy-computed sample sizes at α=0.05, power=0.80.

## SSE Event Protocol

All events are `data: <json>\n\n` formatted. Event types:

| Event | Payload |
|-------|---------|
| `started` | `{ advertisement_id }` |
| `agent_start` | `{ agent }` — emitted once per agent on first event (not re-emitted on loop iterations) |
| `agent_complete` | `{ agent, data, progress, total, advertisement_id }` — emitted on EVERY iteration |
| `image_generating` | `{ advertisement_id }` |
| `image_ready` | `{ data: { url, variant_url }, advertisement_id }` |
| `cancelled` | `{ advertisement_id }` |
| `done` | `{ advertisement_id, status }` |
| `cost_summary` | `{ total_cost_usd, total_latency_ms, per_agent }` |
| `error` | `{ agent, data: { message } }` |

## Inline Schema Migrations

`main.py`'s lifespan handler runs idempotent SQLite migrations after `create_all`:

```python
result = await conn.execute(text("PRAGMA table_info(products)"))
existing_cols = {row[1] for row in result.fetchall()}
if "unit_cost_usd" not in existing_cols:
    await conn.execute(text("ALTER TABLE products ADD COLUMN unit_cost_usd REAL"))
    await conn.commit()
```

This pattern handles adding new columns to existing databases without Alembic.

## Deployment

- **Local**: `uv run uvicorn backend.main:app --reload --port 8000`
- **Docker**: Multi-stage build in `Dockerfile` — builder installs deps with uv, final image copies venv + code
- **Cloud Run**: `cloudbuild.yaml` builds image → pushes to GCR → deploys to Cloud Run (2 vCPU, 2 GB, 600s timeout)
