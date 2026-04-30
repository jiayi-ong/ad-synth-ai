# Ad-Synth AI

A web-based multi-agent platform that turns a product image, product description, and marketing brief into investor-grade ad concepts and a production-ready prompt for static image ad generation.

## Overview

Ad-Synth AI acts as the "marketing brain." A deterministic 7-agent pipeline — built on Google ADK and Vertex AI — researches trends, develops creative strategy, engineers a clean image-generation prompt, and outputs a full suite of marketing recommendations. The final text-to-image model receives only structured creative instructions, not strategy clutter.

```
Product + Brief
      │
      ▼
┌─────────────────────────────────────────┐
│         Ad-Synth AI Pipeline            │
│                                         │
│  1. Product Understanding Agent         │
│  2. Audience & Positioning Agent        │
│  3. Trend Research Agent                │
│  4. Creative Strategy Agent             │
│  5. Persona Agent                       │
│  6. Prompt Engineering Agent            │
│  7. Marketing Recommendation Agent      │
└─────────────────────────────────────────┘
      │
      ▼
Image-Gen Prompt  +  Marketing Output  +  Generated Ad
```

## Features

- **Multi-agent pipeline** — `SequentialAgent` (Google ADK) orchestrates 7 specialist LLM agents in strict order, each reading from and writing to shared session state
- **Trend research** — Google Custom Search + Reddit APIs, with sqlite-vec RAG cache to avoid redundant searches
- **Creative directions** — 3–5 scored concepts (novelty, audience fit, conversion potential, brand fit) with a recommended pick
- **Persistent personas** — reusable AI model personas with demographics, appearance, voice, and values; selectively included/excluded per generation run
- **Mismatch detection** — Audience agent flags product-audience divergences and recommends improvements
- **A/B variant generation** — auto-generates a follow-up prompt that changes exactly one visual element
- **Real-time streaming UI** — SSE stream surfaces each agent's output as it completes, with 7 collapsible transparency tabs
- **Content safety guardrails** — `before_model_callback` blocks prompts containing blocked content before they reach the LLM
- **Graceful error handling** — partial pipeline failures save completed agent outputs; UI renders all available results even if later agents fail
- **Abstract image generation** — pluggable provider interface; ships with Vertex AI Imagen and a mock provider for local dev

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agents | Google ADK (`SequentialAgent`, `LlmAgent`, `FunctionTool`) |
| LLM | Gemini 2.0 Flash (via `google-genai`) |
| Image Generation | Vertex AI Imagen 3 |
| Backend | FastAPI + SQLAlchemy async (aiosqlite) |
| Auth | JWT (python-jose) + bcrypt |
| Trend Cache | sqlite-vec (vector similarity RAG) |
| Frontend | Vanilla HTML/CSS/ES6 (no build step) |
| Package Manager | uv |
| Deployment | Google Cloud Run |

## Project Structure

```
ad-synth-ai/
├── backend/
│   ├── core/          # Config, security, dependencies
│   ├── db/            # SQLAlchemy engine and session
│   ├── models/        # ORM: User, Campaign, Product, Persona, Advertisement
│   ├── schemas/       # Pydantic request/response schemas
│   ├── routers/       # FastAPI routes (auth, campaigns, products, personas, advertisements, generate)
│   ├── services/      # Business logic (auth, CRUD, image generation)
│   └── pipeline/
│       ├── agents/    # 7 LlmAgent definitions
│       ├── orchestrator.py   # SequentialAgent assembly
│       ├── runner.py         # ADK Runner + DatabaseSessionService
│       ├── state_keys.py     # Shared state key constants
│       └── guardrails.py     # Content safety callback
├── prompts/           # Plain .txt prompt files — one per agent (human-editable)
├── tools/             # FunctionTools: Google Search, Reddit, trend cache
├── frontend/          # Single-page app (index.html, CSS, JS modules)
├── tests/             # Pytest unit + integration tests
├── Dockerfile         # Multi-stage uv build
└── cloudbuild.yaml    # Cloud Build → Cloud Run CI/CD
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

### Run Locally

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Open [http://localhost:8000/app](http://localhost:8000/app) in your browser.

The minimum `.env` for a full local run (mock image generation, no GCP required):

```env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_gemini_api_key
IMAGE_GEN_PROVIDER=mock
JWT_SECRET_KEY=dev-secret-change-in-prod
DATABASE_URL=sqlite+aiosqlite:///./data/ad_synth.db
ADK_DATABASE_URL=sqlite+aiosqlite:///./data/adk_sessions.db
```

### Debug Agents Interactively

```bash
uv run adk web backend/pipeline/
```

### Run Tests

```bash
uv run pytest tests/ -v
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Local dev | Gemini API key from Google AI Studio |
| `GOOGLE_GENAI_USE_VERTEXAI` | Prod | `TRUE` to use Vertex AI instead of AI Studio |
| `GCP_PROJECT_ID` | Prod | GCP project ID |
| `IMAGE_GEN_PROVIDER` | Yes | `mock` (local) or `vertexai` (prod) |
| `JWT_SECRET_KEY` | Yes | Secret for JWT signing — use a strong random string in prod |
| `GOOGLE_CSE_API_KEY` | Optional | Google Custom Search API key (trend research) |
| `GOOGLE_CSE_ID` | Optional | Custom Search Engine ID |
| `REDDIT_CLIENT_ID` | Optional | Reddit app client ID (trend research) |
| `REDDIT_CLIENT_SECRET` | Optional | Reddit app client secret |
| `DATABASE_URL` | Yes | SQLAlchemy async DB URL |

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

For production, switch `DATABASE_URL` to Cloud SQL (PostgreSQL) and update `runner.py` to use `VertexAISessionService`.

## Agent Prompts

All agent prompts live in `prompts/` as plain `.txt` files. Each file is loaded at startup and can be edited without touching Python code. Every prompt instructs its agent to output strict JSON conforming to a documented schema.

| File | Agent |
|------|-------|
| `product_agent.txt` | Product type, visual attributes, claims, quality tier |
| `audience_agent.txt` | Audience segments, positioning, mismatch detection |
| `trend_agent.txt` | Web + Reddit research, cache check, trend synthesis |
| `creative_agent.txt` | 3–5 scored creative directions, recommended concept |
| `persona_agent.txt` | Persona selection or synthesis |
| `prompt_agent.txt` | Clean image-gen prompt + A/B variant |
| `marketing_agent.txt` | Slogan, platforms, copy variants, legal risks |

## Key Data Models

- **Campaign** — top-level container with mission, values, and brand guidelines
- **Product** — name, description, and uploaded reference image
- **Persona** — reusable AI model persona with traits JSON (demographics, appearance, voice, beliefs)
- **Advertisement** — links a campaign + product + personas; stores `pipeline_state` JSON (each agent's output), generated image URL, A/B variant, and marketing output

## License

MIT
