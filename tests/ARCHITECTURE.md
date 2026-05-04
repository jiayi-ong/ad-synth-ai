# Tests Architecture

The test suite uses `pytest` with `pytest-asyncio` for async test support. Tests are organized into unit and integration layers.

## Structure

```
tests/
├── conftest.py                         # Shared fixtures: app client, auth headers, DB records
├── unit/
│   ├── test_services/
│   │   ├── test_auth_service.py        # JWT registration, login, wrong password, protected routes
│   │   ├── test_campaign_service.py    # Campaign CRUD, ownership enforcement
│   │   └── test_image_service.py       # Multi-provider factory + each provider's behavior
│   ├── test_agents/
│   │   ├── test_state_keys.py          # State key uniqueness, count, sub-pipeline key isolation
│   │   └── test_trend_pipeline_structure.py  # Pipeline structural validation (agent types, counts)
│   └── test_tools/
│       ├── test_youtube_tools.py       # YouTube API graceful degradation + result normalization
│       ├── test_twitter_tools.py       # Twitter API + SERPAPI fallback on rate limit
│       └── test_serpapi_tools.py       # SERPAPI platform-specific result normalization
└── integration/
    └── test_api_generation.py          # Full generation endpoint with mocked ADK Runner
```

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# With coverage
uv run pytest tests/ --cov=backend --cov=tools --cov-report=term-missing
```

## Fixtures (`conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `client` | function | `TestClient` for the FastAPI app with an in-memory SQLite test DB |
| `auth_headers` | function | `{"Authorization": "Bearer <token>"}` for an auto-registered test user |
| `campaign` | function | A Campaign record created via the API for the test user |
| `product` | function | A Product record created via the API for the test user |

The test database is separate from the dev database — `DATABASE_URL` is overridden to use `sqlite+aiosqlite:///./data/test.db` (or in-memory) in conftest.

## Unit Tests

### `test_image_service.py` — Image Provider Tests

Tests the `create_image_provider()` factory and each provider:

| Test | What It Verifies |
|------|-----------------|
| `test_factory_returns_mock_by_default` | Factory returns `MockImageGenProvider` when no provider configured |
| `test_factory_returns_vertexai` | Factory returns `VertexAIImagenProvider` when `IMAGE_GEN_PROVIDER=vertexai` |
| `test_factory_returns_gemini` | Factory returns `GeminiImageProvider` when `IMAGE_GEN_PROVIDER=gemini` |
| `test_factory_returns_shortapi` | Factory returns `ShortAPIProvider` when `IMAGE_GEN_PROVIDER=shortapi` |
| `test_mock_provider_returns_placeholder` | Mock returns placehold.co URL without API calls |
| `test_shortapi_raises_without_key` | ShortAPIProvider raises `RuntimeError` when `SHORTAPI_API_KEY` unset |
| `test_gemini_provider_extracts_image_part` | Gemini provider correctly extracts `inline_data` from mocked response |

### `test_trend_pipeline_structure.py` — Pipeline Structure Tests

Validates the assembled pipeline structure without running any LLM calls:

| Test | What It Verifies |
|------|-----------------|
| `test_trend_agent_is_sequential` | `trend_research_agent` is a `SequentialAgent` (not `LlmAgent`) |
| `test_trend_agent_name_unchanged` | Outer name is still `trend_research_agent` (backward compat) |
| `test_trend_sub_pipeline_has_five_steps` | Sub-pipeline has exactly 5 sequential steps |
| `test_data_collection_is_parallel` | Step 2 is a `ParallelAgent` |
| `test_data_collection_has_seven_agents` | ParallelAgent has exactly 7 sub-agents |
| `test_trend_critic_writes_trend_research` | `trend_validator_agent` has `output_key == TREND_RESEARCH` |
| `test_trend_keyword_writes_trend_keywords` | `trend_keyword_agent` has `output_key == TREND_KEYWORDS` |

### `test_state_keys.py` — State Contract Tests

| Test | What It Verifies |
|------|-----------------|
| `test_agent_output_keys_count` | `AGENT_OUTPUT_KEYS` has exactly 15 entries |
| `test_state_keys_are_strings` | Key constants are strings, not None or ints |
| `test_all_keys_unique` | No duplicate keys in `AGENT_OUTPUT_KEYS` |
| `test_trend_sub_pipeline_keys_exist` | All 9 intermediate trend keys exist with correct string values |
| `test_trend_sub_pipeline_keys_not_in_agent_output_keys` | Sub-pipeline keys are NOT in `AGENT_OUTPUT_KEYS` |

### Tool Tests

Each tool test file mocks the underlying API client and verifies:
- Returns empty list when the API key is absent (graceful degradation)
- Normalizes API response into the expected `[{field, ...}]` schema
- Handles API errors (HTTP 429 rate limit, network errors) by returning empty list

## Integration Tests (`test_api_generation.py`)

Tests the full HTTP layer of the generation endpoint using a mock ADK Runner that yields pre-canned events.

| Test | What It Verifies |
|------|-----------------|
| `test_generation_endpoint_returns_sse_stream` | POST /generate returns `text/event-stream`, contains `started` and `done` events, at least one `agent_complete` or `image_ready` event |
| `test_generation_requires_auth` | POST /generate returns 401 without auth token |
| `test_ab_variant_requires_existing_ad` | POST /generate/ab-variant returns 404 for non-existent advertisement |

The mock runner yields `MockEvent` objects for all 11 agents in order, simulating a complete pipeline run without calling any real LLM.

## Test Coverage Gaps (Known)

- No tests for individual LlmAgent prompt behavior (requires live LLM calls)
- No tests for Vertex AI image provider (requires GCP credentials)
- No tests for ShortAPI provider with a real endpoint response
- Frontend is not covered by the test suite (vanilla JS, no build step)
