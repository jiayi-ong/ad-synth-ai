# Pipeline Architecture

The pipeline is the core intelligence layer. It uses Google ADK's `SequentialAgent` and `ParallelAgent` primitives to orchestrate 11 specialist LLM agents. All inter-agent communication happens through shared session state — no direct agent-to-agent calls.

## Files

```
pipeline/
├── orchestrator.py     # Assembles the full 11-agent pipeline as a SequentialAgent
├── runner.py           # Creates the ADK Runner + DatabaseSessionService
├── state_keys.py       # All state key constants — the shared contract between agents
├── guardrails.py       # Content safety before_model_callback
├── standalone_runner.py # CLI runner for local testing outside FastAPI
└── agents/             # One file per agent (or sub-pipeline)
    ├── product_agent.py
    ├── audience_agent.py
    ├── trend_agent.py          # Trend sub-pipeline SequentialAgent (wraps trend_agents/)
    ├── competitor_agent.py
    ├── creative_agent.py
    ├── persona_agent.py
    ├── prompt_agent.py
    ├── marketing_agent.py
    ├── evaluation_agent.py
    ├── channel_agent.py
    ├── brand_consistency_agent.py
    └── trend_agents/           # Trend sub-pipeline internals
        ├── __init__.py
        ├── keyword_agent.py    # Keyword extraction (step 1)
        ├── platform_agents.py  # 7 platform LlmAgents + ParallelAgent (step 2)
        ├── aggregator_agent.py # Cross-platform dedup + ranking (step 3)
        ├── synthesis_agent.py  # Product-contextualized synthesis + RAG cache (step 4)
        └── critic_agent.py     # Quality validation gate, writes TREND_RESEARCH (step 5)
```

## Pipeline Structure

```
ad_synthesis_pipeline (SequentialAgent)
│
├── [1] product_understanding_agent    → product_profile
├── [2] audience_positioning_agent     → audience_analysis
│
├── [3] research_parallel (ParallelAgent)
│   ├── trend_research_agent (SequentialAgent)   ← see "Trend Sub-Pipeline" below
│   │       └── ... → trend_research
│   └── competitor_agent               → competitor_analysis
│
├── [4] creative_strategy_agent        → creative_directions
├── [5] persona_agent                  → selected_persona
├── [6] prompt_engineering_agent       → image_gen_prompt + ab_variant_prompt
│
├── [7] synthesis_parallel (ParallelAgent)
│   ├── marketing_recommendation_agent → marketing_output
│   ├── evaluation_agent               → evaluation_output
│   └── channel_adaptation_agent       → channel_adaptation
│
└── [8] brand_consistency_agent        → brand_consistency
```

## Trend Research Sub-Pipeline

The trend research stage is a self-contained `SequentialAgent` named `trend_research_agent` that runs as part of the Stage 3 parallel block. It expands a single "trend research" step into 5 sequential stages:

```
trend_research_agent (SequentialAgent — name kept for backward compat)
│
├── [1] trend_keyword_agent         reads: product_profile, audience_analysis
│                                   writes: trend_keywords (8-12 search terms)
│
├── [2] data_collection_parallel (ParallelAgent — 7 agents simultaneously)
│   ├── youtube_trend_agent         tool: search_youtube_trends()    → youtube_trend_data
│   ├── twitter_trend_agent         tool: search_twitter_trends()    → twitter_trend_data
│   ├── tiktok_trend_agent          tool: search_tiktok_trends()     → tiktok_trend_data
│   ├── instagram_trend_agent       tool: search_instagram_trends()  → instagram_trend_data
│   ├── reddit_trend_agent          tools: search_reddit(), get_trending_posts() → reddit_trend_data
│   ├── web_search_trend_agent      tools: serpapi_web_search(), google_custom_search() → web_search_trend_data
│   └── pinterest_trend_agent       tool: search_pinterest_trends()  → pinterest_trend_data
│
├── [3] trend_aggregator_agent      reads: all 7 platform data keys
│                                   writes: aggregated_trend_data (dedup + ranked)
│
├── [4] trend_synthesis_agent       reads: aggregated_trend_data, product_profile, audience_analysis
│                                   tools: check_trend_cache(), store_trend_cache()
│                                   writes: aggregated_trend_data (product-contextualized)
│
└── [5] trend_critic_agent          reads: aggregated_trend_data, product_profile, audience_analysis
                                    writes: trend_research   ← consumed by downstream agents
```

The `trend_critic_agent` (inner `LlmAgent`) is the agent that writes `TREND_RESEARCH`. The outer `SequentialAgent` wrapper (`trend_research_agent`) does not emit its own final response event — only the inner critic does. This is why `_AGENT_KEY_MAP` in `generation.py` maps `"trend_critic_agent"` → `TREND_RESEARCH`.

## State Keys (`state_keys.py`)

The state key file is the formal contract between all agents. No agent should read or write keys that aren't declared here.

**Input keys** (set by the generation endpoint before pipeline start):

| Key | Description |
|-----|-------------|
| `RAW_PRODUCT_DESCRIPTION` | Product name + description text |
| `RAW_MARKETING_BRIEF` | Assembled marketing brief (audience, value prop, tone, etc.) |
| `CAMPAIGN_ID` | UUID of the current campaign |
| `EXCLUDED_PERSONA_IDS` | List of persona IDs to skip |
| `BRAND_PROFILE_CONTEXT` | JSON-serialized brand profile (if campaign has one) |
| `TARGET_CHANNEL` | Requested ad channel (meta, tiktok, youtube, etc.) |

**Output keys** (written by agents, read by downstream agents and the generation endpoint):

| Key | Written By |
|-----|-----------|
| `PRODUCT_PROFILE` | product_understanding_agent |
| `AUDIENCE_ANALYSIS` | audience_positioning_agent |
| `TREND_RESEARCH` | trend_critic_agent |
| `COMPETITOR_ANALYSIS` | competitor_agent |
| `CREATIVE_DIRECTIONS` | creative_strategy_agent |
| `SELECTED_PERSONA` | persona_agent |
| `IMAGE_GEN_PROMPT` | prompt_engineering_agent |
| `AB_VARIANT_PROMPT` | prompt_engineering_agent |
| `MARKETING_OUTPUT` | marketing_recommendation_agent |
| `EVALUATION_OUTPUT` | evaluation_agent |
| `CHANNEL_ADAPTATION` | channel_adaptation_agent |
| `BRAND_CONSISTENCY` | brand_consistency_agent |
| `PIPELINE_ERROR` | Any agent on failure |

**Trend sub-pipeline intermediate keys** (internal, not in `AGENT_OUTPUT_KEYS`):

`TREND_KEYWORDS`, `YOUTUBE_TREND_DATA`, `TWITTER_TREND_DATA`, `TIKTOK_TREND_DATA`, `INSTAGRAM_TREND_DATA`, `REDDIT_TREND_DATA`, `WEB_SEARCH_TREND_DATA`, `PINTEREST_TREND_DATA`, `AGGREGATED_TREND_DATA`

`AGENT_OUTPUT_KEYS` is an ordered list of the 11 main output keys used by the UI for progress tracking.

## Agent Construction Pattern

Each agent file follows the same pattern:

```python
from google.adk.agents import LlmAgent
from google.genai import types
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import MY_INPUT_KEY, MY_OUTPUT_KEY

def create_my_agent() -> LlmAgent:
    prompt = Path("prompts/my_agent.txt").read_text()
    return LlmAgent(
        name="my_agent",
        model="gemini-2.0-flash",
        instruction=prompt,
        output_key=MY_OUTPUT_KEY,
        tools=[FunctionTool(my_tool_function)],
        before_model_callback=content_safety_callback,
        generate_content_config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
```

All agents:
- Load their prompt from `prompts/<name>.txt` at construction time
- Write a single JSON output to a dedicated `output_key` in session state
- Pass through the content safety `before_model_callback`
- Are configured for JSON-only responses (`response_mime_type="application/json"`)

## Guardrails (`guardrails.py`)

A `before_model_callback` is applied to every agent. It scans the assembled prompt for blocked content patterns (racial bias, violence, sexual content, hate speech) before the LLM call. If triggered, it returns a safe fallback response instead of calling the model.

## Runner (`runner.py`)

The runner wires the pipeline to ADK's execution engine:

```python
runner = Runner(
    agent=pipeline,                        # the top-level SequentialAgent
    app_name="ad_synth_pipeline",
    session_service=DatabaseSessionService(db_url=settings.adk_database_url),
)
```

- `DatabaseSessionService` persists session state to `adk_sessions.db` (SQLite locally, Cloud SQL in prod)
- Sessions are keyed by `(user_id, session_id)` — each advertisement generation gets a fresh session

## Adding a New Agent

1. Create `backend/pipeline/agents/my_new_agent.py` with a `create_my_new_agent()` factory
2. Add a prompt file at `prompts/my_new_agent.txt`
3. Declare any new state keys in `state_keys.py` and add to `AGENT_OUTPUT_KEYS` if it's a main output
4. Add `create_my_new_agent()` to the appropriate stage in `orchestrator.py`
5. Map `"my_new_agent"` → `MY_OUTPUT_KEY` in `generation.py`'s `_AGENT_KEY_MAP`
6. Add to `_NON_CRITICAL_AGENTS` in `generation.py` if failures should be non-fatal
