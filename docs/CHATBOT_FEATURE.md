# AI Chatbot Assistant Feature

## Overview

The chatbot assistant is an informational AI widget that helps users understand the AdSynth platform. It can answer questions about:

- How to use any UI feature (campaigns, products, personas, brand profiles, generation flow, etc.)
- What each of the 16 specialist AI agents does
- What agent output data means (evaluation scores, creative direction scores, pricing analysis, etc.)
- Best practices for getting better results

**Important**: The assistant is read-only. It cannot execute any operations — it cannot generate ads, create campaigns, delete data, or interact with the system in any way.

---

## Architecture

The chatbot is an independent extension of the existing platform. It does not modify the ADK pipeline and uses direct Gemini API calls (not Google ADK agents).

```
Frontend (chatbot.js)          Backend (chatbot router/service)
┌─────────────────────┐        ┌──────────────────────────────┐
│  Fixed widget in    │  JWT   │  POST /chat/session          │
│  document.body      │ ──────▶│  POST /chat/message (SSE)    │
│  (persists across   │        │  DELETE /chat/session        │
│   route changes)   │◀──────  │                              │
└─────────────────────┘  SSE   │  chatbot_service.py          │
                                │  ├── Guardrail check         │
                                │  ├── KB semantic search      │
                                │  ├── Pipeline context fetch  │
                                │  └── Gemini streaming call   │
                                │                              │
                                │  knowledge_base.py           │
                                │  ├── chatbot_knowledge.json  │
                                │  └── numpy similarity search │
                                │                              │
                                │  ChatSession model (DB)      │
                                └──────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Direct Gemini API (not ADK) | Keeps chatbot fully independent of the agent pipeline |
| In-memory numpy similarity search | KB has ~50 static entries — no sqlite-vec DB needed |
| One session per user | Support assistant pattern; `session_id` in API allows future multi-session extension |
| Guardrail as SSE stream (not HTTP error) | Frontend state machine handles all responses uniformly |
| Advertisement context fetched server-side | Client sends only the ID; server validates ownership |

---

## Files

### New Files

| File | Purpose |
|------|---------|
| `backend/models/chat_session.py` | `ChatSession` SQLAlchemy model |
| `backend/schemas/chatbot.py` | Pydantic request/response schemas |
| `backend/services/knowledge_base.py` | Knowledge base load, embed, similarity search |
| `backend/services/chatbot_service.py` | Core logic: guardrails, context assembly, Gemini call |
| `backend/routers/chatbot.py` | FastAPI router with 3 endpoints |
| `data/chatbot_knowledge.json` | Pre-seeded knowledge base (40+ entries) |
| `prompts/chatbot_agent.txt` | System prompt template |
| `frontend/js/chatbot.js` | Self-contained chatbox widget |
| `frontend/css/chatbot.css` | Widget styles (uses existing CSS variables) |
| `tests/unit/test_chatbot/test_guardrails.py` | Guardrail unit tests |
| `tests/unit/test_chatbot/test_knowledge_base.py` | Knowledge base unit tests |
| `tests/unit/test_chatbot/test_chatbot_service.py` | Service logic unit tests |
| `tests/module/test_chatbot_router.py` | Module-tier router tests |

### Modified Files

| File | Change |
|------|--------|
| `backend/models/__init__.py` | Added `ChatSession` import |
| `backend/main.py` | Added chatbot router + KB init in lifespan |
| `backend/core/config.py` | Added 3 chatbot settings |
| `frontend/index.html` | Added `chatbot.css` and `chatbot.js` |
| `frontend/js/api.js` | Added `createChatSession`, `clearChatSession` methods |

---

## API Reference

**Base path**: `/chat`
**Auth**: All endpoints require `Authorization: Bearer <token>`

### `POST /chat/session`

Get or create the user's chat session. Idempotent.

**Response:**
```json
{
  "session_id": "uuid",
  "created": true,
  "message_count": 0
}
```

### `POST /chat/message`

Send a message and receive a streaming SSE response.

**Request body:**
```json
{
  "message": "what does the evaluation agent do?",
  "session_id": "uuid",
  "advertisement_id": "uuid-or-null"
}
```

**SSE events:**
```
data: {"event": "token", "token": "The evaluation agent...", "done": false}
data: {"event": "token", "token": " produces a scorecard", "done": false}
data: {"event": "done", "token": "", "done": true}
```

Error event:
```
data: {"event": "error", "message": "Something went wrong", "done": true}
```

Guardrail refusal (returned as a normal token stream, not HTTP error):
```
data: {"event": "token", "token": "I can explain how that works, but I can't delete anything for you...", "done": false}
data: {"event": "done", "token": "", "done": true}
```

### `DELETE /chat/session`

Clear the user's conversation history (preserves session row).

**Response:**
```json
{"cleared": true}
```

---

## Knowledge Base

### Format (`data/chatbot_knowledge.json`)

```json
[
  {
    "id": "agent_product_profile",
    "category": "agent_explanation",
    "title": "Product Profile Agent",
    "content": "The Product Profile agent is the first agent...",
    "tags": ["product", "agent"],
    "related_state_key": "product_profile"
  }
]
```

**Categories:**
- `agent_explanation` — one entry per agent (16 total), linked to `related_state_key`
- `ui_howto` — platform how-to guides
- `output_explanation` — help understanding agent output fields
- `faq` — common questions

### Semantic Search

At startup, `knowledge_base.py`:
1. Loads all entries from `data/chatbot_knowledge.json`
2. If `data/chatbot_knowledge_vectors.npy` exists, loads precomputed embeddings (fast cold start)
3. Otherwise generates embeddings via `gemini-embedding-001` and saves to `.npy`
4. Stores embeddings as an in-memory `numpy` matrix for fast cosine similarity at query time

On each chat message, top-3 entries above the similarity threshold are injected into the system prompt.

**Precomputing vectors** (run locally before deployment to avoid cold-start embedding API call):
```python
from backend.services.knowledge_base import initialise
initialise(embed_on_startup=True)
# Vectors are saved to data/chatbot_knowledge_vectors.npy
```

---

## Guardrails

### Layer 1 — Pre-LLM keyword scan

Checked before any Gemini API call. Trigger words (whole-word match, case-insensitive):
`generate, create, delete, remove, start, run, execute, add, upload, submit, launch, modify`

When triggered: returns a canned refusal SSE stream immediately, no Gemini call made.

### Layer 2 — System prompt constraint

The system prompt (`prompts/chatbot_agent.txt`) explicitly instructs the model that it cannot perform actions. This handles nuanced cases that pass Layer 1 (e.g., "how would I generate..." — answered, not refused).

---

## Context Management

- **Storage**: `ChatSession.messages` — JSON list of `{"role", "content", "timestamp"}` dicts
- **Truncation**: Before each request, oldest turns are dropped if `len(messages) >= chatbot_max_turns * 2`
- **System prompt**: Rebuilt fresh every request (not stored in history)
- **Pipeline context**: Injected inline into the current user message (not persisted)

---

## Configuration

New settings in `backend/core/config.py` (all optional, can be set via environment variable):

| Variable | Default | Description |
|----------|---------|-------------|
| `CHATBOT_MAX_TURNS` | `20` | Max conversation turns before oldest are dropped |
| `CHATBOT_KNOWLEDGE_THRESHOLD` | `0.82` | Minimum cosine similarity for KB matches |
| `CHATBOT_EMBED_ON_STARTUP` | `true` | Whether to generate embeddings at startup if .npy not found |

---

## GCP Deployment

No additional Cloud Run or Cloud SQL changes needed:

- The `ChatSession` table is created automatically by `Base.metadata.create_all` on first startup
- The chatbot uses Vertex AI via the existing `GOOGLE_GENAI_USE_VERTEXAI` and project credentials
- No new secrets are required
- Optional: add `CHATBOT_EMBED_ON_STARTUP=false` if startup speed is critical (disables KB search until `.npy` is present in the image)

---

## Testing

```bash
# Unit tests (no external services)
pytest tests/unit/test_chatbot/ -v

# Module tests (real DB, mocked Gemini)
pytest tests/module/test_chatbot_router.py -v

# All chatbot tests
pytest tests/unit/test_chatbot/ tests/module/test_chatbot_router.py -v
```

Test coverage:
- Guardrail keyword detection (22 cases)
- Knowledge base load, similarity ranking, threshold filtering
- Conversation truncation logic
- System prompt assembly
- Pipeline context extraction
- Router session idempotency, auth, SSE content-type, guardrail via HTTP
