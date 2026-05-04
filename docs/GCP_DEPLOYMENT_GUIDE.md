# GCP Deployment Guide

This guide covers every GCP resource that must be provisioned before deploying ad-synth-ai to Cloud Run, and explains how to run the first deployment and set up ongoing CI/CD.

For local development, see [LOCAL_DEV_SETUP.md](LOCAL_DEV_SETUP.md).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Enable Required APIs](#2-enable-required-apis)
3. [Create a Service Account and IAM Roles](#3-create-a-service-account-and-iam-roles)
4. [Create Secret Manager Secrets](#4-create-secret-manager-secrets)
5. [First Deployment (Manual)](#5-first-deployment-manual)
6. [CI/CD via Cloud Build Trigger](#6-cicd-via-cloud-build-trigger)
7. [Verify the Deployment](#7-verify-the-deployment)
8. [Environment Variable Reference](#8-environment-variable-reference)
9. [Scaling and Cost Notes](#9-scaling-and-cost-notes)
10. [Production Upgrade: Cloud SQL](#10-production-upgrade-cloud-sql)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

- **gcloud CLI** installed and authenticated:
  ```bash
  gcloud auth login
  gcloud auth application-default login   # needed for Vertex AI SDK
  ```
- **Docker Desktop** installed (for local image builds and testing before Cloud Build)
- A **GCP project** created — note its Project ID (e.g. `my-project-123`)
- **Billing enabled** on the project (Cloud Run, Cloud Build, Vertex AI all require billing)

Set your default project to avoid repeating `--project` on every command:
```bash
gcloud config set project YOUR_PROJECT_ID
```

---

## 2. Enable Required APIs

Run once per project:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com
```

This enables:
| API | Used for |
|-----|----------|
| `run.googleapis.com` | Cloud Run deployment |
| `cloudbuild.googleapis.com` | CI/CD builds |
| `containerregistry.googleapis.com` | Storing Docker images (`gcr.io`) |
| `secretmanager.googleapis.com` | Secure storage of API keys |
| `aiplatform.googleapis.com` | Vertex AI Imagen (image generation) and Gemini |
| `storage.googleapis.com` | GCS bucket for uploaded files (optional for POC) |

---

## 3. Create a Service Account and IAM Roles

The Cloud Run service needs a dedicated identity with least-privilege access. The Cloud Build service account also needs permission to deploy.

### 3a. Create the runner service account

```bash
gcloud iam service-accounts create ad-synth-ai-runner \
  --display-name="Ad Synth AI Cloud Run Runner"
```

### 3b. Grant runtime roles to the runner SA

```bash
SA="ad-synth-ai-runner@YOUR_PROJECT_ID.iam.gserviceaccount.com"

# Access Vertex AI for LLM inference and image generation
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/aiplatform.user"

# Read secrets injected as env vars at container start
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor"

# Write generated images to GCS (only if STORAGE_BACKEND=gcs)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/storage.objectCreator"
```

### 3c. Grant the Cloud Build SA permission to deploy

Cloud Build runs as the Cloud Build service account. It needs to:
- Deploy Cloud Run services
- Pass the runner SA identity to Cloud Run

```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
CB_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

# Deploy Cloud Run services
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$CB_SA" \
  --role="roles/run.admin"

# Pass the runner SA to Cloud Run (--service-account flag in cloudbuild.yaml)
gcloud iam service-accounts add-iam-policy-binding \
  ad-synth-ai-runner@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --member="serviceAccount:$CB_SA" \
  --role="roles/iam.serviceAccountUser"
```

---

## 4. Create Secret Manager Secrets

All secrets referenced in `cloudbuild.yaml` under `--set-secrets` must exist before the first deployment. Optional secrets (trend research APIs) can be created with placeholder values and updated later.

### 4a. Required secrets (must have real values)

```bash
# JWT signing key — generate a strong random string
JWT_VALUE=$(python3 -c "import secrets; print(secrets.token_hex(32))")
printf '%s' "$JWT_VALUE" | gcloud secrets create jwt-secret --data-file=-

# GCP Project ID (used internally by Vertex AI SDK)
printf '%s' "YOUR_PROJECT_ID" | gcloud secrets create gcp-project-id --data-file=-
```

### 4b. Optional trend research secrets

Create these with placeholder values if you don't have the keys yet. The app falls back gracefully when they are empty.

```bash
# Google Custom Search (CSE) — both key and CX ID needed together
printf '%s' "YOUR_KEY_OR_PLACEHOLDER" | gcloud secrets create google-cse-key --data-file=-
printf '%s' "YOUR_CX_OR_PLACEHOLDER" | gcloud secrets create google-cse-id --data-file=-

# YouTube Data API v3 (Google Cloud Console → APIs & Services → YouTube Data API)
printf '%s' "YOUR_KEY_OR_PLACEHOLDER" | gcloud secrets create youtube-api-key --data-file=-

# Reddit API (create an app at https://www.reddit.com/prefs/apps)
printf '%s' "YOUR_CLIENT_ID_OR_PLACEHOLDER" | gcloud secrets create reddit-client-id --data-file=-
printf '%s' "YOUR_CLIENT_SECRET_OR_PLACEHOLDER" | gcloud secrets create reddit-client-secret --data-file=-

# X/Twitter API v2 Bearer Token
printf '%s' "YOUR_TOKEN_OR_PLACEHOLDER" | gcloud secrets create twitter-bearer-token --data-file=-

# SerpAPI (covers Instagram, TikTok, Pinterest, web search fallback)
printf '%s' "YOUR_KEY_OR_PLACEHOLDER" | gcloud secrets create serpapi-key --data-file=-

# ShortAPI (only needed if IMAGE_GEN_PROVIDER=shortapi)
printf '%s' "YOUR_KEY_OR_PLACEHOLDER" | gcloud secrets create shortapi-key --data-file=-
```

To update a secret later with the real value:
```bash
printf '%s' "REAL_API_KEY_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-
```

---

## 5. First Deployment (Manual)

With APIs enabled, IAM configured, and all secrets created, you can run the first build from your local machine:

```bash
# From the repo root
gcloud builds submit --config cloudbuild.yaml .
```

What this does:
1. Uploads the local source tree to Cloud Build (`.gcloudignore` trims unnecessary files)
2. Builds the Docker image in two stages (uv dependency install → slim final image)
3. Pushes the image to Container Registry as both `$COMMIT_SHA` and `latest`
4. Deploys the image to Cloud Run in `us-central1`

First build takes **3–6 minutes** (downloading uv + resolving Python dependencies). Subsequent builds are faster due to Docker layer caching.

> **Note on `uv.lock`**: `uv.lock` is currently excluded from `.gitignore`. For `gcloud builds submit .` (local upload) this is fine — the file is sent from your local filesystem. For CI/CD triggers that clone from git (Section 6), you must commit `uv.lock` to the repository so the builder can find it. Remove the `uv.lock` line from `.gitignore` before setting up triggers.

---

## 6. CI/CD via Cloud Build Trigger

After a successful manual deployment, set up automatic deploys on push to `main`:

```bash
# Connect your GitHub repo (follow the interactive OAuth flow in the console if prompted)
gcloud builds triggers create github \
  --repo-name=ad-synth-ai \
  --repo-owner=YOUR_GITHUB_ORG_OR_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --name="deploy-on-push-to-main"
```

From this point, every `git push origin main` triggers a full build and deploy automatically.

**Before enabling the trigger**: commit `uv.lock` to the repository:
```bash
# In your local repo
git rm --cached uv.lock          # remove from gitignore tracking
# Edit .gitignore and remove the "uv.lock" line
git add uv.lock .gitignore
git commit -m "chore: commit uv.lock for Cloud Build CI"
git push origin main
```

---

## 7. Verify the Deployment

```bash
# Get the Cloud Run service URL
SERVICE_URL=$(gcloud run services describe ad-synth-ai \
  --region=us-central1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Health check (should return {"status":"ok","version":"0.1.0"})
curl "$SERVICE_URL/health"

# Open the UI in a browser
open "$SERVICE_URL/app"       # macOS
start "$SERVICE_URL/app"      # Windows
```

### Viewing logs

```bash
# Stream live logs
gcloud run services logs tail ad-synth-ai --region=us-central1

# Or in the Cloud Logging console:
# Filter: resource.type="cloud_run_revision" AND resource.labels.service_name="ad-synth-ai"
```

Logs are structured JSON (Cloud Logging parses them automatically). Each pipeline run emits per-agent latency and token-cost events.

---

## 8. Environment Variable Reference

All values set in `cloudbuild.yaml`. Non-secret values are in `--set-env-vars`; secrets are injected from Secret Manager via `--set-secrets`.

| Variable | Source | Cloud Run Value | Notes |
|----------|--------|-----------------|-------|
| `GOOGLE_GENAI_USE_VERTEXAI` | env var | `TRUE` | Uses Vertex AI instead of AI Studio |
| `GCP_PROJECT_ID` | Secret Manager | `gcp-project-id:latest` | Used by Vertex AI SDK |
| `GCP_REGION` | env var | `us-central1` | Match the Cloud Run region |
| `GEMINI_MODEL` | env var | `gemini-2.0-flash` | Main LLM for all agents |
| `IMAGE_GEN_PROVIDER` | env var | `vertexai` | Vertex AI Imagen 3.0 |
| `JWT_SECRET_KEY` | Secret Manager | `jwt-secret:latest` | Signs auth tokens |
| `DATABASE_URL` | env var | `sqlite+aiosqlite:///./data/ad_synth.db` | POC: ephemeral SQLite |
| `ADK_DATABASE_URL` | env var | `sqlite+aiosqlite:///./data/adk_sessions.db` | ADK session store |
| `STORAGE_BACKEND` | env var | `local` | `gcs` for persistent uploads |
| `LOG_TO_FILE` | env var | `false` | stdout → Cloud Logging |
| `LOG_FORMAT` | env var | `json` | Structured logs for Cloud Logging |
| `LOG_LEVEL` | env var | `INFO` | |
| `GOOGLE_CSE_API_KEY` | Secret Manager | `google-cse-key:latest` | Google Custom Search |
| `GOOGLE_CSE_ID` | Secret Manager | `google-cse-id:latest` | Search engine CX ID |
| `YOUTUBE_API_KEY` | Secret Manager | `youtube-api-key:latest` | Trend research |
| `REDDIT_CLIENT_ID` | Secret Manager | `reddit-client-id:latest` | Trend research |
| `REDDIT_CLIENT_SECRET` | Secret Manager | `reddit-client-secret:latest` | Trend research |
| `TWITTER_BEARER_TOKEN` | Secret Manager | `twitter-bearer-token:latest` | Trend research |
| `SERPAPI_API_KEY` | Secret Manager | `serpapi-key:latest` | Trend research |
| `SHORTAPI_API_KEY` | Secret Manager | `shortapi-key:latest` | Only for `IMAGE_GEN_PROVIDER=shortapi` |

---

## 9. Scaling and Cost Notes

### Why these Cloud Run settings

| Setting | Value | Reason |
|---------|-------|--------|
| `--concurrency=10` | 10 requests/instance | SSE connections stay open for the full pipeline run (~2–3 min). Default concurrency of 80 would exhaust 2 GiB RAM well before that limit. |
| `--max-instances=5` | 5 | Caps simultaneous capacity. For a demo with a small audience this is generous; reduces surprise bills. |
| `--cpu=2` | 2 vCPU | The async pipeline runs multiple agent stages in parallel (trend research + competitor analysis). Two CPUs improve throughput on the asyncio event loop. |
| `--timeout=600` | 10 min | Full pipeline including retries can take ~3–4 min. 600 s provides headroom. |

### Approximate cost per pipeline run (us-central1)

| Cost item | Estimate |
|-----------|----------|
| Cloud Run CPU/memory (120 s × 2 vCPU × 2 GiB) | ~$0.005 |
| Vertex AI Gemini Flash (all 16 agents) | ~$0.005–$0.02 |
| Vertex AI Imagen 3.0 (1 image) | ~$0.04 |
| **Total per run** | **~$0.05–$0.07** |

Cloud Run bills nothing when idle (no requests in flight).

---

## 10. Production Upgrade: Cloud SQL

The default `DATABASE_URL` uses SQLite on the container's ephemeral filesystem. Data (users, campaigns, brand profiles) is **lost on every new deployment**. For a persistent production database, switch to Cloud SQL PostgreSQL.

### Create a Cloud SQL instance

```bash
gcloud sql instances create ad-synth-ai-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create adsynthai --instance=ad-synth-ai-db

gcloud sql users create adsynthai \
  --instance=ad-synth-ai-db \
  --password=YOUR_STRONG_DB_PASSWORD
```

### Grant Cloud SQL access to the runner SA

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ad-synth-ai-runner@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### Update `cloudbuild.yaml` for Cloud SQL

1. Add the `--add-cloudsql-instances` flag to the `gcloud run deploy` step:
   ```yaml
   - "--add-cloudsql-instances=YOUR_PROJECT_ID:us-central1:ad-synth-ai-db"
   ```

2. Change the `DATABASE_URL` in `--set-env-vars` to use the Unix socket:
   ```
   DATABASE_URL=postgresql+asyncpg://adsynthai:PASSWORD@/adsynthai?host=/cloudsql/YOUR_PROJECT_ID:us-central1:ad-synth-ai-db
   ```
   Store the password as a Secret Manager secret and interpolate it, or embed it in the connection string (less secure).

3. Do the same for `ADK_DATABASE_URL` (same instance, different database name if desired).

4. Add `asyncpg` to the project dependencies:
   ```bash
   uv add asyncpg
   ```

No changes to `backend/db/base.py` are needed — the SQLAlchemy engine creation already handles both SQLite and PostgreSQL URLs correctly.

---

## 11. Troubleshooting

### `PERMISSION_DENIED` when calling Vertex AI

The Cloud Run service account lacks `roles/aiplatform.user`. Re-run Section 3b.

### `Secret not found` during deployment

Run the Secret Manager create commands in Section 4 before re-submitting the build. Every secret name in `--set-secrets` must exist.

### `uv.lock not found` during Cloud Build

Either the lock file is missing from the git repo (see the note in Section 5) or it was accidentally added to `.dockerignore`. Ensure `uv.lock` is committed and not excluded.

### Health check fails immediately after deploy

The container's lifespan creates database tables on startup. If startup takes longer than Cloud Run's probe timeout, increase the startup probe. Check logs:
```bash
gcloud run services logs tail ad-synth-ai --region=us-central1
```

### SSE stream cuts off mid-pipeline

Cloud Run terminates requests that exceed the `--timeout` value. The pipeline can run up to ~4 min under load; 600 s gives ample headroom. If you still see cutoffs, confirm the client is not applying its own timeout (browser EventSource has no built-in timeout, but proxies might).

### Image upload returns 500

If `STORAGE_BACKEND=gcs` is set, the GCS bucket must exist and the runner SA must have `roles/storage.objectCreator`. The current default is `STORAGE_BACKEND=local`, which stores uploads in the container's ephemeral `/app/data/uploads/` directory.

### `cloudbuild.yaml` step fails with `--service-account not found`

The service account `ad-synth-ai-runner@YOUR_PROJECT_ID.iam.gserviceaccount.com` must be created before the first Cloud Build run. Re-run Section 3a if it doesn't exist.
