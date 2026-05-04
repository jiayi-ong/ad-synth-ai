# GCP Deployment Guide

This guide covers every GCP resource that must be provisioned before deploying ad-synth-ai to Cloud Run.

**Local development is unaffected** — it continues to use SQLite via the `DATABASE_URL` in your `.env` file. Only the deployed instance uses Cloud SQL.

For local development setup, see [LOCAL_DEV_SETUP.md](LOCAL_DEV_SETUP.md).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Enable Required APIs](#2-enable-required-apis)
3. [Create a Service Account and IAM Roles](#3-create-a-service-account-and-iam-roles)
4. [Create Cloud SQL Instance](#4-create-cloud-sql-instance)
5. [Create Secret Manager Secrets](#5-create-secret-manager-secrets)
6. [First Deployment (Manual)](#6-first-deployment-manual)
7. [CI/CD via Cloud Build Trigger](#7-cicd-via-cloud-build-trigger)
8. [Verify the Deployment](#8-verify-the-deployment)
9. [Environment Variable Reference](#9-environment-variable-reference)
10. [Scaling and Cost Notes](#10-scaling-and-cost-notes)
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
- **Billing enabled** on the project (Cloud Run, Cloud Build, Vertex AI, Cloud SQL all require billing)

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
  sqladmin.googleapis.com \
  storage.googleapis.com
```

| API | Used for |
|-----|----------|
| `run.googleapis.com` | Cloud Run deployment |
| `cloudbuild.googleapis.com` | CI/CD builds |
| `containerregistry.googleapis.com` | Storing Docker images (`gcr.io`) |
| `secretmanager.googleapis.com` | Secure storage of API keys and DB credentials |
| `aiplatform.googleapis.com` | Vertex AI Imagen (image generation) and Gemini |
| `sqladmin.googleapis.com` | Cloud SQL (persistent PostgreSQL database) |
| `storage.googleapis.com` | GCS bucket for uploaded files (optional) |

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

# Connect to Cloud SQL via the Cloud SQL Auth Proxy
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/cloudsql.client"

# Write uploaded files to GCS (only if STORAGE_BACKEND=gcs)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/storage.objectCreator"
```

### 3c. Grant the Cloud Build SA permission to deploy

```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
CB_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

# Deploy Cloud Run services
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$CB_SA" \
  --role="roles/run.admin"

# Pass the runner SA identity to Cloud Run (required for --service-account flag)
gcloud iam service-accounts add-iam-policy-binding \
  ad-synth-ai-runner@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --member="serviceAccount:$CB_SA" \
  --role="roles/iam.serviceAccountUser"
```

---

## 4. Create Cloud SQL Instance

Cloud SQL provides a persistent PostgreSQL database that survives redeployments. Data you create on the deployed instance (accounts, brand profiles, campaigns, ads) is preserved across every future deploy.

> **Local dev is unchanged** — your `.env` still points to SQLite and local testing works as before.

### 4a. Create the instance

```bash
gcloud sql instances create ad-synth-ai-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1
```

`db-f1-micro` (1 shared vCPU, 614 MB RAM) is the smallest tier — sufficient for a POC. Startup takes 2–3 minutes.

### 4b. Create the database and user

```bash
gcloud sql databases create adsynthai --instance=ad-synth-ai-db

# Choose a strong password and note it — you'll use it in Section 5
gcloud sql users create adsynthai \
  --instance=ad-synth-ai-db \
  --password=YOUR_STRONG_DB_PASSWORD
```

Cloud Run connects to Cloud SQL via a Unix socket (`/cloudsql/...`) injected by the Cloud SQL Auth Proxy — no public IP or firewall rules needed.

---

## 5. Create Secret Manager Secrets

All secrets referenced in `cloudbuild.yaml` under `--set-secrets` must exist before the first deployment. Optional secrets (trend research APIs) can be created with placeholder values.

### 5a. Required secrets

```bash
# JWT signing key
JWT_VALUE=$(python3 -c "import secrets; print(secrets.token_hex(32))")
printf '%s' "$JWT_VALUE" | gcloud secrets create jwt-secret --data-file=-

# GCP Project ID (used internally by Vertex AI SDK)
printf '%s' "YOUR_PROJECT_ID" | gcloud secrets create gcp-project-id --data-file=-

# Cloud SQL connection string — replace YOUR_PROJECT_ID and YOUR_STRONG_DB_PASSWORD
printf '%s' "postgresql+asyncpg://adsynthai:YOUR_STRONG_DB_PASSWORD@/adsynthai?host=/cloudsql/YOUR_PROJECT_ID:us-central1:ad-synth-ai-db" \
  | gcloud secrets create database-url --data-file=-
```

### 5b. Optional trend research secrets

Create with placeholder values if you don't have the keys yet — the app falls back gracefully when they are empty.

```bash
printf '%s' "placeholder" | gcloud secrets create google-cse-key --data-file=-
printf '%s' "placeholder" | gcloud secrets create google-cse-id --data-file=-
printf '%s' "placeholder" | gcloud secrets create youtube-api-key --data-file=-
printf '%s' "placeholder" | gcloud secrets create reddit-client-id --data-file=-
printf '%s' "placeholder" | gcloud secrets create reddit-client-secret --data-file=-
printf '%s' "placeholder" | gcloud secrets create twitter-bearer-token --data-file=-
printf '%s' "placeholder" | gcloud secrets create serpapi-key --data-file=-
printf '%s' "placeholder" | gcloud secrets create shortapi-key --data-file=-
```

To update a secret later with the real value:
```bash
printf '%s' "REAL_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-
```

---

## 6. First Deployment (Manual)

With APIs enabled, IAM configured, Cloud SQL created, and all secrets in place:

```bash
# From the repo root — first update the lock file to include asyncpg
uv add asyncpg

# Submit the build
gcloud builds submit --config cloudbuild.yaml .
```

What happens:
1. Local source tree (trimmed by `.gcloudignore`) is uploaded to Cloud Build
2. Docker image is built in two stages (uv dependency install → slim runtime)
3. Image is pushed to Container Registry tagged with commit SHA and `latest`
4. Cloud Run is deployed with Cloud SQL attached — SQLAlchemy creates all tables on first startup

First build takes **4–7 minutes**. Subsequent builds are faster due to Docker layer caching.

> **Note on `uv.lock`**: `uv.lock` is currently in `.gitignore`. For `gcloud builds submit .` (local upload) this works fine. For CI/CD triggers that clone from git (Section 7), the lock file must be committed — see Section 7 for instructions.

---

## 7. CI/CD via Cloud Build Trigger

After a successful manual deployment, set up automatic deploys on push to `main`:

```bash
gcloud builds triggers create github \
  --repo-name=ad-synth-ai \
  --repo-owner=YOUR_GITHUB_ORG_OR_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --name="deploy-on-push-to-main"
```

**Before enabling the trigger**, commit `uv.lock` so Cloud Build can find it when cloning:
```bash
# Remove uv.lock from .gitignore (delete the "uv.lock" line)
git rm --cached uv.lock
git add uv.lock .gitignore
git commit -m "chore: commit uv.lock for Cloud Build CI"
git push origin main
```

---

## 8. Verify the Deployment

```bash
SERVICE_URL=$(gcloud run services describe ad-synth-ai \
  --region=us-central1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Health check — should return {"status":"ok","version":"0.1.0"}
curl "$SERVICE_URL/health"

# Open the UI
open "$SERVICE_URL/app"       # macOS
start "$SERVICE_URL/app"      # Windows
```

### Viewing logs

```bash
gcloud run services logs tail ad-synth-ai --region=us-central1
```

Or in Cloud Logging console, filter: `resource.type="cloud_run_revision" AND resource.labels.service_name="ad-synth-ai"`

Logs are structured JSON. Each pipeline run emits per-agent latency and token-cost events.

---

## 9. Environment Variable Reference

| Variable | Source | Cloud Run Value | Notes |
|----------|--------|-----------------|-------|
| `GOOGLE_GENAI_USE_VERTEXAI` | env var | `TRUE` | Uses Vertex AI instead of AI Studio |
| `GCP_PROJECT_ID` | Secret Manager | `gcp-project-id:latest` | Used by Vertex AI SDK |
| `GCP_REGION` | env var | `us-central1` | Matches Cloud Run region |
| `GEMINI_MODEL` | env var | `gemini-2.0-flash` | Main LLM for all agents |
| `IMAGE_GEN_PROVIDER` | env var | `vertexai` | Vertex AI Imagen 3.0 |
| `JWT_SECRET_KEY` | Secret Manager | `jwt-secret:latest` | Signs auth tokens |
| `DATABASE_URL` | Secret Manager | `database-url:latest` | PostgreSQL via Cloud SQL Unix socket |
| `ADK_DATABASE_URL` | env var | `sqlite+aiosqlite:///./data/adk_sessions.db` | ADK session store; ephemeral is fine |
| `STORAGE_BACKEND` | env var | `local` | Change to `gcs` for persistent image uploads |
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

**Local dev**: `DATABASE_URL` in `.env` stays as `sqlite+aiosqlite:///./data/ad_synth.db` — no change needed.

---

## 10. Scaling and Cost Notes

### Cloud Run settings

| Setting | Value | Reason |
|---------|-------|--------|
| `--concurrency=10` | 10 req/instance | SSE connections stay open ~2–3 min per pipeline run. Default of 80 would exhaust 2 GiB RAM. |
| `--max-instances=5` | 5 | Caps capacity for a small-audience demo; limits surprise billing. |
| `--cpu=2` | 2 vCPU | Parallel pipeline stages (trend research + competitor analysis) benefit from 2 CPUs on the asyncio event loop. |
| `--timeout=600` | 10 min | Full pipeline including retries can take ~3–4 min. 600 s gives headroom. |

### Approximate cost per pipeline run (us-central1)

| Item | Estimate |
|------|----------|
| Cloud Run CPU/memory (~120 s × 2 vCPU × 2 GiB) | ~$0.005 |
| Vertex AI Gemini Flash (all 16 agents) | ~$0.005–$0.02 |
| Vertex AI Imagen 3.0 (1 image) | ~$0.04 |
| Cloud SQL db-f1-micro (always on) | ~$7–10/month |
| **Per-run total** | **~$0.05–$0.07** |

Cloud Run bills nothing when idle. Cloud SQL bills continuously (even when idle) — stop the instance when not needed to save cost:
```bash
gcloud sql instances patch ad-synth-ai-db --activation-policy=NEVER   # stop
gcloud sql instances patch ad-synth-ai-db --activation-policy=ALWAYS  # start
```

---

## 11. Troubleshooting

### `PERMISSION_DENIED` when calling Vertex AI

The runner SA lacks `roles/aiplatform.user`. Re-run Section 3b.

### `Secret not found` during deployment

Every secret in `--set-secrets` must exist in Secret Manager before the build. Re-run Section 5.

### `database-url` secret causes connection error on startup

Check that the Cloud SQL instance name in the URL exactly matches `YOUR_PROJECT_ID:us-central1:ad-synth-ai-db`. The runner SA must have `roles/cloudsql.client` (Section 3b) and the `--add-cloudsql-instances` flag must be present in `cloudbuild.yaml`.

### `uv.lock not found` during Cloud Build

The lock file is missing from the git repo. See Section 7 for instructions on committing it.

### Health check fails immediately after deploy

Check startup logs — Cloud SQL table creation runs on first boot and takes a few seconds. If the probe timeout is too tight:
```bash
gcloud run services logs tail ad-synth-ai --region=us-central1
```

### SSE stream cuts off mid-pipeline

Cloud Run terminates requests at the `--timeout` value. The pipeline runs ~3–4 min; 600 s gives ample headroom. If cutoffs still occur, check whether a proxy (load balancer, corporate firewall) is imposing a shorter timeout.

### `cloudbuild.yaml` step fails with `--service-account not found`

The SA `ad-synth-ai-runner@YOUR_PROJECT_ID.iam.gserviceaccount.com` must be created before the Cloud Build run. Re-run Section 3a.
