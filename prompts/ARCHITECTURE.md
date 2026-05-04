# Prompts Architecture

All agent prompts are stored as plain `.txt` files in this directory. They are loaded at agent construction time and can be edited without modifying any Python code.

## Design Principles

- **Human-editable**: Product and marketing domain experts can tune agent behavior without touching the codebase.
- **JSON-first**: Every prompt instructs its agent to output a strict JSON object conforming to a documented schema. This schema is the contract between agents.
- **Self-contained**: Each prompt includes its own schema definition so the LLM has the full contract in context.
- **State-aware**: Prompts reference specific session state keys by name (e.g., `{product_profile}`, `{audience_analysis?}`) so the LLM knows which prior outputs to use.

## Loading Pattern

```python
from pathlib import Path

prompt_text = (Path(__file__).parents[3] / "prompts" / "my_agent.txt").read_text(encoding="utf-8")

agent = LlmAgent(instruction=prompt_text, ...)
```

## ADK Template Injection — Critical Rules

ADK scans the **entire** prompt text (including code blocks) with `r'{+[^{}]*}+'` and substitutes values from session state. Violations crash the pipeline at runtime.

1. **Never use `{var}` syntax in code examples** — use string concatenation:
   - ❌ `print(f'CHART_BASE64:{b64}')` → crashes with `KeyError: 'b64'`
   - ✅ `print('CHART_BASE64:' + b64)`

2. **Use `{key?}` for optional inputs** — ADK injects empty string when the key is absent; `{key}` without `?` raises `KeyError` if missing.

3. **All non-optional `{key}` references must be pre-seeded** in `initial_state` before pipeline start if the key might not be set when the agent runs (see `generation.py`).

## Prompt Files

### Main Pipeline Agents

| File | Agent | Reads From State | Writes To State |
|------|-------|-----------------|-----------------|
| `product_agent.txt` | Product Understanding | `raw_product_description`, `raw_marketing_brief` | `product_profile` |
| `market_segmentation_agent.txt` | Market Segmentation | `product_profile`, `raw_marketing_brief`, `loop_feedback?` | `market_segmentation` |
| `loop_evaluator_agent.txt` | Loop Evaluator | `market_segmentation`, `audience_analysis` | `loop_eval_signal`, `loop_feedback` |
| `audience_agent.txt` | Audience & Positioning | `product_profile`, `raw_marketing_brief`, `market_segmentation`, `loop_feedback`, `extra_input` | `audience_analysis` |
| `competitor_agent.txt` | Competitor Analysis | `product_profile`, `audience_analysis` | `competitor_analysis` |
| `pricing_analysis_agent.txt` | Pricing Analysis | `product_profile`, `market_segmentation`, `competitor_analysis?` | `pricing_analysis` |
| `creative_agent.txt` | Creative Strategy | `product_profile`, `audience_analysis`, `trend_research?`, `competitor_analysis?`, `market_segmentation?`, `pricing_analysis?`, `extra_input` | `creative_directions` |
| `persona_agent.txt` | Persona Selection | `audience_analysis`, `creative_directions`, `extra_input` | `selected_persona` |
| `prompt_agent.txt` | Prompt Engineering | `raw_product_description`, `product_profile`, `audience_analysis`, `creative_directions`, `selected_persona?`, `extra_input` | `image_gen_prompt`, `ab_variant_prompt` |
| `campaign_architecture_agent.txt` | Campaign Architecture | `product_profile`, `audience_analysis`, `market_segmentation`, `pricing_analysis`, `creative_directions`, `selected_persona?` | `campaign_architecture` |
| `experiment_design_agent.txt` | Experiment Design | `campaign_architecture`, `audience_analysis`, `market_segmentation` | `experiment_design` |
| `marketing_agent.txt` | Marketing Recommendations | `product_profile`, `audience_analysis`, `creative_directions`, `extra_input` | `marketing_output` |
| `evaluation_agent.txt` | Ad Evaluation | `product_profile`, `audience_analysis`, `creative_directions`, `extra_input` | `evaluation_output` |
| `channel_agent.txt` | Channel Adaptation | `creative_directions`, `target_channel`, `extra_input` | `channel_adaptation` |
| `brand_consistency_agent.txt` | Brand Consistency | `brand_profile_context`, `creative_directions`, `extra_input` | `brand_consistency` |

### Trend Sub-Pipeline Agents

| File | Agent | Reads From State | Writes To State |
|------|-------|-----------------|-----------------|
| `trend_keyword_agent.txt` | Keyword Extraction | `product_profile`, `audience_analysis` | `trend_keywords` |
| `trend_youtube_agent.txt` | YouTube Platform | `trend_keywords` via tool | `youtube_trend_data` |
| `trend_twitter_agent.txt` | Twitter Platform | `trend_keywords` via tool | `twitter_trend_data` |
| `trend_tiktok_agent.txt` | TikTok Platform | `trend_keywords` via tool | `tiktok_trend_data` |
| `trend_instagram_agent.txt` | Instagram Platform | `trend_keywords` via tool | `instagram_trend_data` |
| `trend_reddit_agent.txt` | Reddit Platform | `trend_keywords` via tool | `reddit_trend_data` |
| `trend_web_agent.txt` | Web Search Platform | `trend_keywords` via tool | `web_search_trend_data` |
| `trend_pinterest_agent.txt` | Pinterest Platform | `trend_keywords` via tool | `pinterest_trend_data` |
| `trend_aggregator_agent.txt` | Trend Aggregator | all 7 `*_trend_data` keys | `aggregated_trend_data` |
| `trend_synthesis_agent.txt` | Trend Synthesis | `aggregated_trend_data`, `product_profile`, `audience_analysis` | `aggregated_trend_data` (refined + charts) |
| `trend_validator_agent.txt` | Trend Validator | `aggregated_trend_data`, `product_profile`, `audience_analysis` | `trend_research` |

### Search Agents (used in older pipeline stages)

| File | Agent | Purpose |
|------|-------|---------|
| `web_search_agent.txt` | Web Search | Google CSE + SERPAPI web search |
| `reddit_search_agent.txt` | Reddit Search | PRAW Reddit search |
| `trend_query_agent.txt` | Trend Query | Query formulation for search agents |

## Output Schema Standards

All main pipeline agents include these standard fields in their output schemas:

```json
{
  "data_provenance": {
    "facts": ["list of claims directly stated in input data"],
    "inferences": ["list of claims logically derived from facts"],
    "assumptions": ["list of estimates with no direct evidence"]
  },
  "readiness_score": {
    "completeness": 0.0,
    "source_grounding": 0.0,
    "confidence": 0.0,
    "risk_level": "low | medium | high"
  }
}
```

Analytical agents (`market_segmentation`, `pricing_analysis`, `experiment_design`) also produce:

```json
{
  "charts": [
    {
      "title": "Chart Title",
      "description": "What this chart shows",
      "image_base64": "<base64-encoded PNG>"
    }
  ]
}
```

Charts are produced by calling `execute_python` with matplotlib code. The code prints `'CHART_BASE64:' + b64` (concatenation, not f-string) to stdout for capture.

## Prompt Structure

Each prompt follows a consistent structure:

```
[Role description]
You are the <Name> Agent in a multi-agent advertising synthesis pipeline.
Your job is to <primary responsibility>.

## Inputs from session state
- `key_name`: Description of what this key contains.
- `optional_key` (optional): Description.

## <Input Section>
{key_name}

## <Optional Input Section (if any)>
{optional_key?}

## Your Responsibilities
1. Numbered list of what to do.
2. MANDATORY: Call <tool> to produce ...

## Output Format
Your response MUST be a valid JSON object and NOTHING ELSE.

{
  "field_name": "type — description",
  ...
}
```

## Editing Guidelines

- The `## Output Format` section defines the schema consumed by downstream agents — changing field names requires updating the downstream agent's prompt and any renderer code.
- Never write `{variable}` in code examples inside a prompt — ADK treats it as a template injection attempt.
- Platform agent prompts (`trend_*_agent.txt`) reference specific tool function names — if a tool is renamed, update the prompt.
- Agents should be instructed to handle empty optional inputs gracefully (output minimal valid JSON, never fabricate data).
- The `?` suffix (`{key?}`) marks an optional template variable. ADK injects empty string when the key is absent instead of raising KeyError.
