# Ad-Synth AI

An AI-powered Creative Operating System for performance marketing. Turns a product description and marketing brief into structured ad concepts, production-ready image-generation prompts, and a full campaign intelligence suite — using a 16-agent multi-agent pipeline with real-time streaming.

## Overview

Ad-Synth AI acts as a campaign intelligence and iteration engine. A hierarchical agent pipeline — built on Google ADK and Vertex AI — runs market segmentation and audience positioning in a feedback loop, researches trends across 7 platforms simultaneously, models pricing with Python-executed financial analysis, designs statistically-grounded A/B experiments, and generates a complete marketing suite. A persistent "Brand Brain" stores company and brand context across campaigns.

```
Product Description + Marketing Brief
              │
              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   Ad-Synth AI Pipeline (16 agents)                   │
│                                                                      │
│  Stage 1:  Product Understanding Agent                               │
│  Stage 2:  [LOOP — up to 3 iterations]                               │
│    ├── Market Segmentation Agent  (TAM/SAM, attractiveness scores)   │
│    ├── Audience & Positioning Agent                                  │
│    └── Loop Evaluator Agent  (calls exit_loop at convergence ≥ 0.80) │
│  Stage 3:  [PARALLEL]                                                │
│    ├── Trend Research Sub-Pipeline  (5 steps, 7 platforms)           │
│    └── Competitor Analysis Agent                                     │
│  Stage 4:  Pricing Analysis Agent  (financial model + charts)        │
│  Stage 5:  Creative Strategy Agent                                   │
│  Stage 6:  Persona Agent                                             │
│  Stage 7:  Prompt Engineering Agent                                  │
│  Stage 8:  Campaign Architecture Agent                               │
│  Stage 9:  Experiment Design Agent  (scipy power analysis)           │
│  Stage 10: [PARALLEL]                                                │
│    ├── Marketing Recommendation Agent                                │
│    ├── Ad Evaluation Agent                                           │
│    └── Channel Adaptation Agent                                      │
│  Stage 11: Brand Consistency Agent                                   │
└──────────────────────────────────────────────────────────────────────┘
              │
              ▼
  Image-Gen Prompt + A/B Variant + Full Marketing Suite + Generated Ad
```

### Positioning ↔ Segmentation Loop (Stage 2)

Stage 2 is an ADK `LoopAgent` (max 3 iterations). The loop evaluator computes a convergence score on three criteria — segment alignment, USP-pain-point coverage, positioning specificity — and calls `exit_loop` when it reaches ≥ 0.80. Feedback from each iteration is written to state (`loop_feedback`) so subsequent iterations can course-correct.

### Trend Research Sub-Pipeline

The trend research stage is a 5-step nested pipeline running 7 platform agents in parallel:

```
trend_keyword_agent (keyword extraction)
        │
        ▼
[PARALLEL — 7 platforms simultaneously]
  YouTube │ Twitter │ TikTok │ Instagram │ Reddit │ Web │ Pinterest
        │
        ▼
trend_aggregator_agent (deduplication + ranking)
        │
        ▼
trend_synthesis_agent (product-contextualized synthesis + RAG cache)
        │
        ▼
trend_validator_agent (quality validation → writes TREND_RESEARCH)
```

## Features

- **16-agent orchestrated pipeline** — `SequentialAgent` wrapping a `LoopAgent`, two `ParallelAgent` groups, and 9 sequential stages; all agents communicate through shared session state
- **Bidirectional positioning↔segmentation loop** — Market Segmentation and Audience Positioning iterate up to 3× with convergence scoring; loop feedback propagates to the next iteration
- **Financial modeling** — Pricing Analysis Agent executes numpy/matplotlib code to produce break-even curves, margin sensitivity charts, and segment-level pricing recommendations
- **Statistical experiment design** — Experiment Design Agent uses `scipy.stats` power analysis to compute sample sizes and render power curves for A/B tests
- **Campaign architecture** — phased campaign blueprint with budget allocation, key messages by segment, and success metrics
- **Multi-namespace knowledge store** — `knowledge_store_tools.py` maintains a sqlite-vec RAG store with namespaces (`competitor`, `market_research`, `pricing_benchmarks`) that accumulates cross-campaign intelligence
- **7-platform trend intelligence** — YouTube, Twitter/X, TikTok, Instagram, Reddit, Web, Pinterest queried concurrently with graceful fallback when keys are absent
- **Brand Brain** — persistent brand profiles (company → brand → product hierarchy) injected as context into every generation run
- **Multi-provider image generation** — pluggable provider abstraction with 4 implementations: Mock, Vertex AI Imagen 3, Gemini native image gen, ShortAPI (Flux/DALL-E/SD)
- **Creative directions** — 3–5 scored concepts (novelty, audience fit, conversion potential, brand fit)
- **Compliance flagging** — Product agent detects regulated advertising categories (health claims, supplements, financial products, alcohol, children's products, gambling, pharma) and outputs `compliance_flags`
- **Data provenance tagging** — Every analytical agent classifies each claim as FACT / INFERENCE / ASSUMPTION and outputs a `readiness_score` (completeness, source grounding, confidence, risk level)
- **Persistent reusable personas** — AI model personas with demographics, appearance, voice, values; selectively included/excluded per run
- **A/B variant generation** — auto-generates a second prompt that changes exactly one visual element
- **Channel-aware adaptation** — platform-specific creative for Meta, TikTok, YouTube, etc.
- **Real-time streaming UI** — SSE stream surfaces each agent's output as it completes, with 16 collapsible tabs, chart rendering, readiness score grid, and live cost tracking
- **Content safety guardrails** — `before_model_callback` blocks flagged content before LLM calls
- **RAG caches** — sqlite-vec stores for trend synthesis and multi-namespace knowledge store
- **Graceful error handling** — non-critical agent failures are isolated; partial results saved and displayed
- **Unit cost tracking** — Products carry `unit_cost_usd` used to anchor the pricing fallback model

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Orchestration | Google ADK (`SequentialAgent`, `ParallelAgent`, `LoopAgent`, `LlmAgent`, `FunctionTool`) |
| LLM | Gemini 2.0 Flash (via `google-genai`) |
| Image Generation | Vertex AI Imagen 3 / Gemini native / ShortAPI (Flux, DALL-E, SD) / Mock |
| Backend | FastAPI + SQLAlchemy async (`aiosqlite` local, Cloud SQL prod) |
| Auth | JWT (`python-jose`) + bcrypt |
| Vector Cache | sqlite-vec (trend cache + multi-namespace knowledge store) |
| Scientific Computing | numpy, matplotlib (financial charts), scipy + statsmodels (power analysis) |
| Social APIs | YouTube Data API v3, Twitter API v2 (Tweepy), Reddit (PRAW), SERPAPI |
| Frontend | Vanilla HTML/CSS/ES6 — no build step, hash-based SPA |
| Package Manager | uv |
| Deployment | Google Cloud Run + Cloud Build CI/CD |

## Project Structure

```
ad-synth-ai/
├── backend/
│   ├── core/           # Config (Pydantic Settings), auth, dependencies, logging middleware
│   ├── db/             # SQLAlchemy async engine and session factory
│   ├── models/         # ORM: User, Campaign, Product (+ unit_cost_usd), Persona, Advertisement, BrandProfile, ResearchCache
│   ├── schemas/        # Pydantic request/response schemas
│   ├── routers/        # FastAPI routes: auth, brands, campaigns, products, personas, ads, generate, evaluate, research
│   ├── services/       # Business logic: auth, CRUD services, image provider factory
│   └── pipeline/
│       ├── agents/         # 16 main LlmAgent + LoopAgent definitions
│       │   ├── positioning_segmentation_loop.py  # LoopAgent wrapping market_seg + audience + loop_eval
│       │   ├── market_segmentation_agent.py
│       │   ├── loop_evaluator_agent.py
│       │   ├── pricing_analysis_agent.py
│       │   ├── campaign_architecture_agent.py
│       │   ├── experiment_design_agent.py
│       │   └── trend_agents/   # 5-agent trend sub-pipeline (keyword, platform×7, aggregator, synthesis, validator)
│       ├── orchestrator.py     # Full 11-stage SequentialAgent assembly
│       ├── runner.py           # ADK Runner + DatabaseSessionService
│       ├── state_keys.py       # All state key constants + DOWNSTREAM_KEYS map
│       └── guardrails.py       # Content safety before_model_callback
├── prompts/            # Plain .txt prompt files — one per agent, human-editable
├── tools/              # FunctionTools: search, Reddit, YouTube, Twitter, SERPAPI, trend cache, knowledge store, code execution
├── frontend/           # Single-page app (index.html + CSS + JS modules, no build step)
├── tests/              # Pytest unit + integration tests
├── Dockerfile          # Multi-stage uv build
└── cloudbuild.yaml     # Cloud Build → Cloud Run CI/CD pipeline
```

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `pip install uv`
- A [Google AI Studio](https://aistudio.google.com/) API key (for local dev without GCP)

### Local Setup

```bash
git clone <repo-url>
cd ad-synth-ai

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env — set GOOGLE_API_KEY at minimum
```

### Minimal `.env` for local dev

The following is sufficient for a full local run — no GCP credentials required:

```env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_gemini_api_key

IMAGE_GEN_PROVIDER=mock

JWT_SECRET_KEY=dev-secret-change-in-prod
DATABASE_URL=sqlite+aiosqlite:///./data/ad_synth.db
ADK_DATABASE_URL=sqlite+aiosqlite:///./data/adk_sessions.db
```

All trend research API keys are optional — tools return empty results gracefully when absent.

### Run Locally

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Open [http://localhost:8000/app](http://localhost:8000/app) in your browser.

### Debug Agents Interactively (ADK Dev UI)

```bash
uv run adk web backend/pipeline/
```

### Run Tests

```bash
uv run pytest tests/ -v
```

## Environment Variables

### Core (Required)

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Gemini API key from Google AI Studio (local dev) |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` to use Vertex AI (Cloud Run prod), `FALSE` for AI Studio |
| `GCP_PROJECT_ID` | GCP project ID (required when using Vertex AI) |
| `JWT_SECRET_KEY` | Secret for JWT signing — use a strong random string in prod |
| `DATABASE_URL` | SQLAlchemy async DB URL (`sqlite+aiosqlite:///./data/ad_synth.db` locally) |
| `ADK_DATABASE_URL` | ADK session DB URL |

### Image Generation (pick one provider)

| Variable | Description |
|----------|-------------|
| `IMAGE_GEN_PROVIDER` | `mock` (placeholder, default) / `vertexai` / `gemini` / `shortapi` |
| `GEMINI_IMAGE_MODEL` | Gemini image model ID (default: `gemini-2.0-flash-exp-image-generation`) |
| `SHORTAPI_API_KEY` | ShortAPI.io key (enables Flux, DALL-E, Stable Diffusion) |
| `SHORTAPI_MODEL` | ShortAPI model (default: `flux-1.1-pro`) |

### Trend Research (all optional — tools degrade gracefully)

| Variable | Description |
|----------|-------------|
| `GOOGLE_CSE_API_KEY` | Google Custom Search API key |
| `GOOGLE_CSE_ID` | Custom Search Engine ID |
| `REDDIT_CLIENT_ID` | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Reddit app client secret |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `TWITTER_BEARER_TOKEN` | Twitter/X API v2 Bearer Token |
| `SERPAPI_API_KEY` | SERPAPI key (covers TikTok, Instagram, Pinterest, Twitter fallback, web) |

### Observability

| Variable | Description |
|----------|-------------|
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` (default: `INFO`) |
| `LOG_FORMAT` | `json` (GCP Cloud Logging) or `text` (human-readable) |

## Deployment (Google Cloud Run)

```bash
gcloud run deploy ad-synth-ai \
  --source . \
  --region us-central1 \
  --memory 2Gi --cpu 2 \
  --timeout 600 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,IMAGE_GEN_PROVIDER=vertexai" \
  --set-secrets "JWT_SECRET_KEY=jwt-secret:latest,GOOGLE_CSE_API_KEY=cse-key:latest"
```

For production: switch `DATABASE_URL` to Cloud SQL (PostgreSQL) and update `runner.py` to use `VertexAISessionService`.

CI/CD is configured in `cloudbuild.yaml` — push to main triggers a build → push to GCR → deploy to Cloud Run.

## Agent Prompts

All prompts live in `prompts/` as plain `.txt` files, loaded at startup. Edit them without touching Python code. Each prompt instructs its agent to output strict JSON conforming to a documented schema.

| File | Agent | Key Output |
|------|-------|------------|
| `product_agent.txt` | Product Understanding | `product_profile` (+ `compliance_flags`, `readiness_score`) |
| `market_segmentation_agent.txt` | Market Segmentation | `market_segmentation` (+ TAM/SAM, charts) |
| `loop_evaluator_agent.txt` | Loop Evaluator | `loop_eval_signal`, `loop_feedback` |
| `audience_agent.txt` | Audience & Positioning | `audience_analysis` (+ `readiness_score`) |
| `competitor_agent.txt` | Competitor Analysis | `competitor_analysis` (+ `competitor_pricing`) |
| `pricing_analysis_agent.txt` | Pricing Analysis | `pricing_analysis` (+ break-even charts) |
| `creative_agent.txt` | Creative Strategy | `creative_directions` (+ `readiness_score`) |
| `persona_agent.txt` | Persona Selection | `selected_persona` |
| `prompt_agent.txt` | Prompt Engineering | `image_gen_prompt`, `ab_variant_prompt` |
| `campaign_architecture_agent.txt` | Campaign Architecture | `campaign_architecture` (phases, budget %, metrics) |
| `experiment_design_agent.txt` | Experiment Design | `experiment_design` (+ scipy power curve) |
| `marketing_agent.txt` | Marketing Recommendations | `marketing_output` (+ `readiness_score`) |
| `evaluation_agent.txt` | Ad Evaluation | `evaluation_output` (+ `readiness_score`) |
| `channel_agent.txt` | Channel Adaptation | `channel_adaptation` |
| `brand_consistency_agent.txt` | Brand Consistency | `brand_consistency` (+ `readiness_score`) |
| `trend_keyword_agent.txt` | Trend Keyword Extraction | `trend_keywords` |
| `trend_{platform}_agent.txt` ×7 | Platform Specialists | `*_trend_data` |
| `trend_aggregator_agent.txt` | Trend Aggregator | `aggregated_trend_data` |
| `trend_synthesis_agent.txt` | Trend Synthesis | `aggregated_trend_data` (refined, + charts) |
| `trend_validator_agent.txt` | Trend Validator | `trend_research` |

## Key Data Models

| Model | Description |
|-------|-------------|
| `Campaign` | Top-level container; links to a `BrandProfile` |
| `BrandProfile` | Persistent brand context: company, mission, values, tone keywords, guidelines |
| `Product` | Name, description, reference image path, `unit_cost_usd` (anchors pricing fallback) |
| `Persona` | Reusable AI model persona — demographics, appearance, voice, values (JSON) |
| `Advertisement` | Links campaign + product + personas; stores full `pipeline_state` JSON, image URLs, A/B variant, status |
| `ResearchCache` | sqlite-vec backed store for RAG-retrieved trend research |

## License

MIT
