# Local Development Setup Guide

This guide covers everything needed to run **ad-synth-ai** locally — from the minimal single-key setup to a fully GCP-linked environment.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| uv | latest | `pip install uv` or [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| git | any | system package manager |
| gcloud CLI | latest | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) *(Track C only)* |

---

## Initial Setup (all tracks)

```bash
git clone <repo-url>
cd ad-synth-ai
uv sync                    # installs all dependencies into .venv
cp .env.example .env       # create your local config
```

---

## Track A — Minimal Local Dev (AI Studio key only)

Everything works at this level: the full 11-agent pipeline runs and mock images are returned instantly.

### 1. Get a Google Gemini API key

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Sign in with a Google account
3. Click **Get API key** → **Create API key**
4. Copy the key

### 2. Configure `.env`

```env
# ── Required ──────────────────────────────────────────────────────────────────
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_key_from_ai_studio_here

# ── Reasonable defaults ───────────────────────────────────────────────────────
IMAGE_GEN_PROVIDER=mock
JWT_SECRET_KEY=dev-secret-local
DATABASE_URL=sqlite+aiosqlite:///./data/ad_synth.db
ADK_DATABASE_URL=sqlite+aiosqlite:///./data/adk_sessions.db
LOG_LEVEL=INFO
LOG_FORMAT=text
```

All trend research keys are **optional** — if unset, those pipeline stages return empty results gracefully without crashing.

### 3. Start the server

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000/app` in your browser.

### What works at this level

| Feature | Status |
|---------|--------|
| Full 11-agent pipeline | ✅ |
| Ad generation (text outputs) | ✅ |
| Mock image placeholder | ✅ |
| Campaign / brand / persona CRUD | ✅ |
| Research Hub (cached results) | ✅ |
| Ad Library | ✅ |
| Real image generation | ❌ (Track B) |
| Trend research (live) | ❌ (Track D) |
| Vertex AI / GCP features | ❌ (Track C) |

### Debug agents interactively (optional)

```bash
uv run adk web backend/pipeline/
```

Opens the ADK developer UI at `http://localhost:8001` — lets you step through individual agents.

---

## Track B — Real Image Generation (no GCP needed)

### Option 1: Gemini native image generation

Uses the same `GOOGLE_API_KEY` from Track A — no extra setup needed.

```env
IMAGE_GEN_PROVIDER=gemini
GEMINI_IMAGE_MODEL=gemini-2.0-flash-exp-image-generation
```

**Note:** Gemini image generation is experimental and may be rate-limited on free tier.

### Option 2: ShortAPI (aggregated provider — Flux, DALL-E, SD)

1. Sign up at [shortapi.io](https://shortapi.io)
2. Get your API key from the dashboard

```env
IMAGE_GEN_PROVIDER=shortapi
SHORTAPI_API_KEY=your_shortapi_key
SHORTAPI_MODEL=flux-1.1-pro    # or: dall-e-3, stable-diffusion-xl
```

### Option 3: Vertex AI Imagen 3 (requires Track C)

```env
IMAGE_GEN_PROVIDER=vertexai
IMAGEN_MODEL=imagen-3.0-generate-002
```

This requires GCP authentication — continue to Track C.

---

## Track C — GCP / Vertex AI Linked

This enables Vertex AI LLM inference and Imagen image generation locally, using the same credentials as the Cloud Run deployment.

### Step 1: Create a GCP project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown → **New Project**
3. Note your **Project ID** (e.g., `ad-synth-ai-dev`)

### Step 2: Enable required APIs

In the GCP Console → **APIs & Services** → **Enable APIs**:

```
Vertex AI API
Cloud Storage API             (if using GCS storage)
Cloud Run API                 (for deployment only)
Secret Manager API            (for deployment only)
```

Or via CLI:
```bash
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID
gcloud services enable storage.googleapis.com --project=YOUR_PROJECT_ID
```

### Step 3: Authenticate locally

**Option A — Application Default Credentials (recommended for dev)**

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

This creates credentials at `~/.config/gcloud/application_default_credentials.json` that are picked up automatically by the Google SDKs.

Verify it worked:
```bash
gcloud auth application-default print-access-token
```

**Option B — Service Account key file**

1. GCP Console → **IAM & Admin** → **Service Accounts** → **Create**
2. Grant roles: `Vertex AI User`, `Storage Object Admin` (if using GCS)
3. **Keys** tab → **Add Key** → **JSON** → download file
4. Set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
```

Add to your shell profile (`~/.bashrc` or `~/.zshrc`) to persist.

### Step 4: Configure `.env`

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GEMINI_MODEL=gemini-2.0-flash

# For Vertex AI image generation:
IMAGE_GEN_PROVIDER=vertexai
IMAGEN_MODEL=imagen-3.0-generate-002
```

**Remove `GOOGLE_API_KEY`** (or leave it — it is ignored when `GOOGLE_GENAI_USE_VERTEXAI=TRUE`).

### Step 5: (Optional) Google Cloud Storage for uploads

Create a GCS bucket:
```bash
gcloud storage buckets create gs://your-bucket-name \
  --project=YOUR_PROJECT_ID \
  --location=us-central1
```

Configure in `.env`:
```env
STORAGE_BACKEND=gcs
GCS_BUCKET=your-bucket-name
```

### Step 6: Verify the connection

```bash
bash scripts/run_tests.sh connection
```

The connection tests will validate your Vertex AI and GCS access and display clear pass/fail per service.

---

## Track D — Trend Research APIs

All APIs are optional and independently configurable. The pipeline degrades gracefully — any absent key causes that platform's data to be skipped with a log warning.

### API Reference Table

| Platform | API Name | Where to get | `.env` variable | Free tier |
|----------|----------|-------------|-----------------|-----------|
| Web search | Google Custom Search | [console.cloud.google.com](https://console.cloud.google.com) → APIs → Custom Search | `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID` | 100 queries/day |
| Instagram / TikTok / Pinterest / Twitter fallback | SERPAPI | [serpapi.com](https://serpapi.com) | `SERPAPI_API_KEY` | 100 searches/month |
| Reddit | Reddit PRAW | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | Unlimited (rate-limited) |
| YouTube | YouTube Data API v3 | [console.cloud.google.com](https://console.cloud.google.com) → APIs → YouTube Data | `YOUTUBE_API_KEY` | 10,000 units/day |
| Twitter / X | X API v2 | [developer.twitter.com](https://developer.twitter.com) | `TWITTER_BEARER_TOKEN` | ~500 searches/month (free tier) |

### Google Custom Search Engine setup

The CSE requires two values:

1. **API key**: GCP Console → APIs & Services → Credentials → Create API Key
   - Enable `Custom Search API`
   - Set `GOOGLE_CSE_API_KEY=your_key`

2. **Search Engine ID**: [programmablesearchengine.google.com](https://programmablesearchengine.google.com)
   - Create a new search engine → set to search the entire web
   - Copy the **Search engine ID** (cx= parameter)
   - Set `GOOGLE_CSE_ID=your_cx_value`

### Reddit PRAW setup

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) (logged in)
2. Click **Create App** → select **script**
3. Fill in any name and redirect URI (`http://localhost`)
4. Copy **client id** (under app name) and **secret**

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=ad-synth-ai/0.1
```

### YouTube Data API v3 setup

1. GCP Console → APIs & Services → **YouTube Data API v3** → Enable
2. APIs & Services → Credentials → **Create Credentials** → API Key
3. (Optional) Restrict key to YouTube Data API v3

```env
YOUTUBE_API_KEY=your_youtube_key
```

### Twitter / X API v2 setup

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Apply for developer access (free tier available)
3. Create a project and app
4. Under **Keys and Tokens** → copy **Bearer Token**

```env
TWITTER_BEARER_TOKEN=your_bearer_token
```

Note: Free tier provides ~500 search calls/month. The pipeline uses SERPAPI as fallback if Twitter is absent.

---

## Running Tests

```bash
# Fast tests only (unit + module, no real API calls):
bash scripts/run_tests.sh

# With connection checks (validates your API keys):
bash scripts/run_tests.sh connection

# Full end-to-end with real Gemini pipeline:
bash scripts/run_tests.sh system

# Everything:
bash scripts/run_tests.sh all
```

Test results are saved to `logs/test_results_<timestamp>.log`.

---

## Log Files

When the server runs, structured logs are written to:

| File | Contents |
|------|----------|
| `logs/app.log` | All application logs (rotating, 10 MB × 5 files) |
| `logs/pipeline.log` | Per-agent completion records with latency and token cost |
| `logs/api.log` | HTTP request logs (method, path, status, latency) |
| `logs/pytest.log` | Test run logs (DEBUG level) |

Set `LOG_TO_FILE=false` to disable file logging (useful for Cloud Run where stdout is preferred).

---

## Troubleshooting

### `ModuleNotFoundError: google.adk`
Run `uv sync` — the ADK package isn't installed yet.

### `401 Unauthorized` on `/generate`
Your JWT token expired. Log out and log back in via the UI, or check `JWT_EXPIRE_HOURS` in `.env`.

### Pipeline hangs indefinitely
- Check Gemini quota: [aistudio.google.com/quota](https://aistudio.google.com/quota)
- Set `LOG_LEVEL=DEBUG` and restart — detailed ADK logs show which agent stalled
- Check `logs/pipeline.log` for partial completions

### `google.api_core.exceptions.PermissionDenied` (Vertex AI)
- ADC is not configured: run `gcloud auth application-default login`
- Vertex AI API not enabled: `gcloud services enable aiplatform.googleapis.com`
- Wrong project: `gcloud config set project YOUR_PROJECT_ID`

### `google.api_core.exceptions.ResourceExhausted`
Gemini free-tier quota hit. Either wait for quota reset or switch to a paid tier. You can also temporarily lower `GEMINI_MODEL` to a lighter model.

### Database errors on startup
Delete `data/ad_synth.db` and `data/adk_sessions.db` — they will be recreated on next startup.

### Image generation returns placeholder despite `IMAGE_GEN_PROVIDER=gemini`
Gemini image model requires `GOOGLE_API_KEY` to be set even when `GOOGLE_GENAI_USE_VERTEXAI=FALSE`. Check `logs/app.log` for the specific error.

### Port 8000 already in use
```bash
# Find and kill the process:
lsof -i :8000        # macOS/Linux
netstat -ano | findstr :8000   # Windows
```

Or start on a different port: `uv run uvicorn backend.main:app --reload --port 8001`
