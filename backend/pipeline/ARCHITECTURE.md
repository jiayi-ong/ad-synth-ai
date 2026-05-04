# Pipeline Architecture

The pipeline is the core intelligence layer. It uses Google ADK's `SequentialAgent`, `ParallelAgent`, `LoopAgent`, and `LlmAgent` primitives to orchestrate 16 specialist agents. All inter-agent communication happens through shared session state — no direct agent-to-agent calls.

## Files

```
pipeline/
├── orchestrator.py              # Assembles the full 11-stage pipeline as a SequentialAgent
├── runner.py                    # Creates the ADK Runner + DatabaseSessionService
├── state_keys.py                # All state key constants + DOWNSTREAM_KEYS map
├── guardrails.py                # Content safety before_model_callback
├── pipeline_logger.py           # Structured JSON logger for pipeline lifecycle events
└── agents/
    ├── product_agent.py
    ├── positioning_segmentation_loop.py  # LoopAgent (max 3 iter) — wraps the three agents below
    ├── market_segmentation_agent.py
    ├── loop_evaluator_agent.py
    ├── audience_agent.py
    ├── trend_pipeline.py        # Trend SequentialAgent sub-pipeline
    ├── competitor_agent.py
    ├── pricing_analysis_agent.py
    ├── creative_agent.py
    ├── persona_agent.py
    ├── prompt_agent.py
    ├── campaign_architecture_agent.py
    ├── experiment_design_agent.py
    ├── marketing_agent.py
    ├── evaluation_agent.py
    ├── channel_agent.py
    ├── brand_consistency_agent.py
    └── trend_agents/            # Trend sub-pipeline internals
        ├── keyword_agent.py
        ├── platform_agents.py   # 7 platform LlmAgents + ParallelAgent
        ├── aggregator_agent.py
        ├── synthesis_agent.py
        └── validator_agent.py   # Writes TREND_RESEARCH (formerly critic_agent)
```

## Pipeline Structure

```
ad_synthesis_pipeline (SequentialAgent)
│
├── [1]  product_understanding_agent    → product_profile
│          (+ compliance_flags, data_provenance, readiness_score)
│
├── [2]  positioning_segmentation_loop (LoopAgent, max_iterations=3)
│    └── loop_body (SequentialAgent)
│         ├── market_segmentation_agent    → market_segmentation
│         │     tools: execute_python, check_knowledge_store, store_knowledge_store
│         ├── audience_positioning_agent   → audience_analysis
│         └── loop_evaluator_agent         → loop_eval_signal  (internal)
│               tool: exit_loop
│               writes: loop_feedback (for next iteration)
│
├── [3]  research_parallel (ParallelAgent)
│    ├── trend_research_pipeline (SequentialAgent)  → trend_research
│    └── competitor_agent                           → competitor_analysis
│         tool: store_knowledge_store (namespace="competitor")
│
├── [4]  pricing_analysis_agent         → pricing_analysis
│          tools: execute_python, check_knowledge_store, store_knowledge_store
│          (financial model: break-even curve, margin scenarios, charts)
│
├── [5]  creative_strategy_agent        → creative_directions
│
├── [6]  persona_agent                  → selected_persona
│
├── [7]  prompt_engineering_agent       → image_gen_prompt + ab_variant_prompt
│
├── [8]  campaign_architecture_agent    → campaign_architecture
│          (phased blueprint, budget allocation, key messages by segment)
│
├── [9]  experiment_design_agent        → experiment_design
│          tool: execute_python (scipy power analysis, power curve chart)
│
├── [10] synthesis_parallel (ParallelAgent)
│    ├── marketing_recommendation_agent → marketing_output
│    ├── evaluation_agent               → evaluation_output
│    └── channel_adaptation_agent       → channel_adaptation
│
└── [11] brand_consistency_agent        → brand_consistency
```

## Trend Research Sub-Pipeline

The trend research stage is a self-contained `SequentialAgent` that runs as one branch of Stage 3's parallel block:

```
trend_research_pipeline (SequentialAgent)
│
├── [1] trend_keyword_agent       reads: product_profile, audience_analysis
│                                 writes: trend_keywords
│
├── [2] data_collection_parallel (ParallelAgent — 7 simultaneously)
│   ├── youtube_trend_agent       tool: search_youtube_trends()
│   ├── twitter_trend_agent       tool: search_twitter_trends()
│   ├── tiktok_trend_agent        tool: search_tiktok_trends()
│   ├── instagram_trend_agent     tool: search_instagram_trends()
│   ├── reddit_trend_agent        tools: search_reddit(), get_trending_posts()
│   ├── web_search_trend_agent    tools: serpapi_web_search(), google_custom_search()
│   └── pinterest_trend_agent     tool: search_pinterest_trends()
│
├── [3] trend_aggregator_agent    reads: all 7 *_trend_data keys
│                                 writes: aggregated_trend_data
│
├── [4] trend_synthesis_agent     tools: check_trend_cache(), store_trend_cache()
│                                 writes: aggregated_trend_data (refined + charts)
│
└── [5] trend_validator_agent     reads: aggregated_trend_data
                                  writes: trend_research  ← consumed downstream
```

`_AGENT_KEY_MAP` in `generation.py` maps `"trend_validator_agent"` → `TREND_RESEARCH`. The outer `SequentialAgent` wrapper does not emit its own final response event.

## State Keys (`state_keys.py`)

The state key file is the formal contract between all agents.

**Input keys** (set before pipeline runs):

| Key | Description |
|-----|-------------|
| `RAW_PRODUCT_DESCRIPTION` | Product name + description text (includes `Unit Cost` line if set) |
| `RAW_MARKETING_BRIEF` | Assembled marketing brief (audience, value prop, tone, etc.) |
| `CAMPAIGN_ID` | UUID of the current campaign |
| `EXCLUDED_PERSONA_IDS` | List of persona IDs to skip |
| `BRAND_PROFILE_CONTEXT` | JSON-serialized brand profile (if campaign has one) |
| `TARGET_CHANNEL` | Requested ad channel (`meta`, `tiktok`, `youtube`, etc.) |
| `EXTRA_INPUT` | Optional user context injected before a stage re-run (pre-seeded `""`) |

**Pre-seeded optional keys** (must be in `initial_state` to prevent ADK template injection KeyErrors):

| Key | Pre-seed Value | Reason |
|-----|---------------|--------|
| `LOOP_FEEDBACK` | `""` | Written by loop_evaluator on iter≥2; referenced by market_seg on iter 1 |
| `MARKET_SEGMENTATION` | `""` | Non-critical loop output; referenced by pricing/campaign/experiment agents |
| `PRICING_ANALYSIS` | `""` | Non-critical agent; referenced by campaign_architecture before it runs |
| `CAMPAIGN_ARCHITECTURE` | `""` | Non-critical agent; referenced by experiment_design before it runs |

Note: `SELECTED_PERSONA` does **not** need pre-seeding — `campaign_architecture_agent.txt` uses `{selected_persona?}` (optional injection). If persona_agent fails, the key is absent and ADK injects an empty string rather than raising a KeyError.

**Main output keys** (written by agents, drive UI progress):

| Key | Written By |
|-----|-----------|
| `PRODUCT_PROFILE` | product_understanding_agent |
| `MARKET_SEGMENTATION` | market_segmentation_agent |
| `AUDIENCE_ANALYSIS` | audience_positioning_agent |
| `TREND_RESEARCH` | trend_validator_agent |
| `COMPETITOR_ANALYSIS` | competitor_agent |
| `PRICING_ANALYSIS` | pricing_analysis_agent |
| `CREATIVE_DIRECTIONS` | creative_strategy_agent |
| `SELECTED_PERSONA` | persona_agent |
| `IMAGE_GEN_PROMPT` | prompt_engineering_agent |
| `CAMPAIGN_ARCHITECTURE` | campaign_architecture_agent |
| `EXPERIMENT_DESIGN` | experiment_design_agent |
| `MARKETING_OUTPUT` | marketing_recommendation_agent |
| `EVALUATION_OUTPUT` | evaluation_agent |
| `CHANNEL_ADAPTATION` | channel_adaptation_agent |
| `BRAND_CONSISTENCY` | brand_consistency_agent |

**Loop-internal keys** (not in `AGENT_OUTPUT_KEYS`):

| Key | Description |
|-----|-------------|
| `LOOP_EVAL_SIGNAL` | Written by loop_evaluator_agent (no UI tab) |
| `LOOP_FEEDBACK` | Correction notes written by loop_evaluator for the next iteration |

**Trend sub-pipeline intermediates**: `TREND_KEYWORDS`, `YOUTUBE_TREND_DATA`, `TWITTER_TREND_DATA`, `TIKTOK_TREND_DATA`, `INSTAGRAM_TREND_DATA`, `REDDIT_TREND_DATA`, `WEB_SEARCH_TREND_DATA`, `PINTEREST_TREND_DATA`, `AGGREGATED_TREND_DATA`, `QUANTITATIVE_INSIGHTS`, `SENTIMENT_INSIGHTS`

`AGENT_OUTPUT_KEYS` is an ordered list of the 15 main output keys used by the UI for progress tracking (image_generation is tracked separately, making 16 total).

## Agent Construction Pattern

Each agent file follows the same pattern:

```python
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types as genai_types
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import MY_OUTPUT_KEY

_NO_THINKING = genai_types.GenerateContentConfig(
    thinking_config=genai_types.ThinkingConfig(thinking_budget=0)
)

def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")

def _build() -> LlmAgent:
    return LlmAgent(
        name="my_agent",
        model=settings.gemini_model,
        include_contents='none',          # see Context Management note below
        instruction=_load_prompt("my_agent"),
        output_key=MY_OUTPUT_KEY,
        generate_content_config=_NO_THINKING,
        tools=[FunctionTool(my_tool)],
        before_model_callback=content_safety_callback,
    )

my_agent = _build()

def build_my_agent() -> LlmAgent:
    """Factory for use inside LoopAgent (each iteration needs a fresh instance)."""
    return _build()
```

Agents that participate in a `LoopAgent` expose a `build_*` factory. The singleton instance (`my_agent`) is used for the sequential stages.

### Context Management: `_NO_THINKING` and `include_contents='none'`

All agents use `_NO_THINKING` (`thinking_budget=0`) to suppress extended thinking tokens. At high input context sizes (~44k+ tokens), thinking tokens can cause `MALFORMED_FUNCTION_CALL` errors even for agents with tools — `thinking_budget=0` prevents this.

Most mid/late-pipeline agents set `include_contents='none'`. **Important limitation**: inside a `SequentialAgent`, `include_contents='none'` does not significantly reduce context because ADK's `_get_current_turn_contents` always finds the previous agent's final response and includes all events from that point forward. The practical effect is minimal for sequential stages beyond the first few.

**`include_contents='none'` must NOT be set on agents inside a `LoopAgent`** (e.g., `market_segmentation_agent`). Within a LoopAgent with multi-tool AFC, this combination causes 0 output even at small context sizes. LoopAgent-hosted agents should use the default `include_contents` value (`'default'`).

## ADK Template Injection Rules

ADK scans the full prompt text with `r'{+[^{}]*}+'` and substitutes session state values. This applies to ALL text including code blocks and JSON examples.

**Rules:**
1. Never write `{variable}` syntax in code examples inside prompts — use string concatenation (`'CHART_BASE64:' + b64`) instead of f-strings.
2. Every `{key}` in a prompt must be present in session state. For optional inputs, use `{key?}` (ADK injects empty string if missing).
3. Non-critical agents whose upstream inputs may be missing should use `{key?}` (e.g., `{competitor_analysis?}` in pricing_analysis_agent.txt).
4. Pre-seed optional keys in `initial_state` before pipeline start (see table above).

## LoopAgent State and DatabaseSessionService

ADK's `DatabaseSessionService` does **not** commit state to the database between sub-agent calls within a LoopAgent iteration. Reading from `session_service.get_session()` after a loop sub-agent's `is_final_response()` event will return the pre-seeded value, not the agent's output.

**Solution**: Read state from `event.actions.state_delta` first (always current, in-memory):

```python
raw_output = None
try:
    delta = (getattr(event.actions, "state_delta", None) or {}) if event.actions else {}
    raw_output = delta.get(state_key)
except Exception:
    pass
if raw_output is None and event.content and event.content.parts:
    text_parts = [p.text for p in event.content.parts if getattr(p, "text", None)]
    if text_parts:
        raw_output = text_parts[-1]
if raw_output is None:
    current_session = await runner.session_service.get_session(...)
    raw_output = current_session.state.get(state_key, "")
```

## Loop Progress Counting

The loop fires `is_final_response()` once per agent per iteration (up to 3×). Use `completed_state_keys: set[str]` to count only the first completion of each state key toward the progress bar:

```python
completed_state_keys: set[str] = set()
# ...
is_first_completion = state_key not in completed_state_keys and state_key != LOOP_EVAL_SIGNAL
if is_first_completion:
    progress += 1
    completed_state_keys.add(state_key)
# Always emit agent_complete SSE (tab content updates on every iteration)
yield _sse("agent_complete", {"agent": state_key, "data": parsed, "progress": progress, ...})
```

## Guardrails (`guardrails.py`)

A `before_model_callback` is applied to every agent. It scans the assembled prompt for blocked content patterns (racial bias, violence, sexual content, hate speech) before the LLM call. If triggered, it returns a safe fallback response instead of calling the model.

## Runner (`runner.py`)

The runner wires the pipeline to ADK's execution engine:

```python
runner = Runner(
    agent=pipeline,
    app_name="ad_synth_ai",
    session_service=DatabaseSessionService(db_url=settings.adk_database_url),
    artifact_service=InMemoryArtifactService(),
)
```

Sessions are keyed by `(user_id, session_id)` — each advertisement generation gets a fresh session (`f"ad_{ad_id}"`), re-runs use `f"rerun_{ad_id}_{stage_key}_{timestamp}"`.

## Non-Critical Agents

The following agents are in `_NON_CRITICAL_AGENTS` — their failures don't stop the pipeline. Partial output is surfaced in the UI:

- `trend_validator_agent`
- `competitor_agent`
- `pricing_analysis_agent`
- `campaign_architecture_agent`
- `experiment_design_agent`
- `marketing_recommendation_agent`
- `evaluation_agent`
- `channel_adaptation_agent`
- `brand_consistency_agent`

## Post-Pipeline Fallbacks

After the pipeline completes, `generation.py` runs two deterministic fallbacks before triggering image generation:

**Pricing fallback** (`compute_pricing_fallback` in `pricing_analysis_agent.py`): If `PRICING_ANALYSIS` is absent or empty, reads `unit_cost_usd` from `PRODUCT_PROFILE` and computes margin scenarios at 2×, 3×, and 5× cost multipliers. Written back to `ad.pipeline_state[PRICING_ANALYSIS]` so the UI always has a pricing anchor. Sets `_fallback: True` on the result.

**Experiment design fallback** (`compute_experiment_design_fallback` in `experiment_design_agent.py`): If `EXPERIMENT_DESIGN` is absent or empty, generates 3 concrete A/B experiments (hook copy, CTA text, audience targeting) using scipy to compute real two-proportion z-test sample sizes at α=0.05, power=0.80. Falls back to hardcoded sample sizes if scipy is unavailable. Sets `_fallback: True` on the result.

Both fallbacks fire only when the corresponding agent produced no output (state key empty). If the agent succeeded, its output is preserved.

## Adding a New Agent

1. Create `backend/pipeline/agents/my_new_agent.py` with `_build()` + singleton + factory; include `_NO_THINKING` in `generate_content_config`; use `include_contents='none'` unless the agent runs inside a LoopAgent
2. Add a prompt file at `prompts/my_new_agent.txt` — never use `{var}` syntax in code examples; use `{key?}` for any optional inputs
3. Declare any new state keys in `state_keys.py`; add to `AGENT_OUTPUT_KEYS` and `DOWNSTREAM_KEYS`
4. Add to `orchestrator.py` in the correct pipeline position
5. Map `"my_new_agent"` → `MY_OUTPUT_KEY` in `generation.py`'s `_AGENT_KEY_MAP`
6. Add to `_NON_CRITICAL_AGENTS` if failures should be non-fatal
7. Pre-seed the output key in `initial_state` if downstream agents reference it as a required template variable (`{key}` not `{key?}`) and it might not be set when they run
8. If the agent can fail at high context and produces critical output, add a deterministic fallback function to the agent file and wire it in `generation.py` after the pipeline completes (see `compute_pricing_fallback` and `compute_experiment_design_fallback` for the pattern)
