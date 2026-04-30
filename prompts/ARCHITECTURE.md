# Prompts Architecture

All agent prompts are stored as plain `.txt` files in this directory. They are loaded at agent construction time and can be edited without modifying any Python code.

## Design Principles

- **Human-editable**: Product and marketing domain experts can tune agent behavior without touching the codebase.
- **JSON-first**: Every prompt instructs its agent to output a strict JSON object conforming to a documented schema. This schema is the contract between agents.
- **Self-contained**: Each prompt includes its own schema definition so the LLM has the full contract in context.
- **State-aware**: Prompts reference specific session state keys by name (e.g., `product_profile`, `audience_analysis`) so the LLM knows which prior outputs to use.

## Loading Pattern

```python
from pathlib import Path

prompt_text = Path("prompts/product_agent.txt").read_text(encoding="utf-8")

agent = LlmAgent(
    instruction=prompt_text,
    ...
)
```

## Prompt Files

### Main Pipeline Agents

| File | Agent | Reads From State | Writes To State |
|------|-------|-----------------|-----------------|
| `product_agent.txt` | Product Understanding | `raw_product_description` | `product_profile` |
| `audience_agent.txt` | Audience & Positioning | `product_profile`, `raw_marketing_brief` | `audience_analysis` |
| `competitor_agent.txt` | Competitor Analysis | `product_profile`, `audience_analysis` | `competitor_analysis` |
| `creative_agent.txt` | Creative Strategy | `product_profile`, `audience_analysis`, `trend_research`, `competitor_analysis` | `creative_directions` |
| `persona_agent.txt` | Persona Selection | `audience_analysis`, `creative_directions` + persona library | `selected_persona` |
| `prompt_agent.txt` | Prompt Engineering | `product_profile`, `creative_directions`, `selected_persona`, `brand_consistency` | `image_gen_prompt`, `ab_variant_prompt` |
| `marketing_agent.txt` | Marketing Recommendations | `product_profile`, `audience_analysis`, `creative_directions` | `marketing_output` |
| `evaluation_agent.txt` | Ad Evaluation | `image_gen_prompt`, `creative_directions`, `audience_analysis` | `evaluation_output` |
| `channel_agent.txt` | Channel Adaptation | `image_gen_prompt`, `creative_directions`, `target_channel` | `channel_adaptation` |
| `brand_consistency_agent.txt` | Brand Consistency | `image_gen_prompt`, `brand_profile_context` | `brand_consistency` |

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
| `trend_synthesis_agent.txt` | Trend Synthesis | `aggregated_trend_data`, `product_profile`, `audience_analysis` | `aggregated_trend_data` (refined) |
| `trend_critic_agent.txt` | Trend Critic | `aggregated_trend_data`, `product_profile`, `audience_analysis` | `trend_research` |

### Legacy Search Agents (used in earlier pipeline stages)

| File | Agent | Purpose |
|------|-------|---------|
| `web_search_agent.txt` | Web Search | Google CSE + SERPAPI web search |
| `reddit_search_agent.txt` | Reddit Search | PRAW Reddit search |
| `trend_query_agent.txt` | Trend Query | Query formulation for search agents |

## Prompt Structure

Each prompt follows a consistent structure:

```
[Role description]
You are the <Name> Agent in a multi-agent advertising synthesis pipeline.
Your job is to <primary responsibility>.

## Inputs from session state
- `key_name`: Description of what this key contains.

## Your Responsibilities
1. Numbered list of what to do.

## [Constraints / Principles / Guidelines]
- Domain-specific rules for this agent.

## Output Format
Your response MUST be a valid JSON object and NOTHING ELSE.

{
  "field_name": "type — description",
  ...
}
```

## Editing Guidelines

- The `## Output Format` section defines the schema consumed by downstream agents — changing field names requires updating the downstream agent's prompt and any code that reads the state key.
- Platform agent prompts (`trend_*_agent.txt`) reference specific tool function names — if a tool is renamed, update the corresponding prompt.
- Prompts should instruct agents to handle empty inputs gracefully (e.g., if all platform data is empty, output minimal valid JSON with empty arrays — never fabricate data).
