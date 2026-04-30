# Contract between all pipeline agents.
# Every key used in context.state must be defined here.

# ── Inputs (set before pipeline runs) ────────────────────────────────────────
RAW_PRODUCT_DESCRIPTION = "raw_product_description"
RAW_MARKETING_BRIEF = "raw_marketing_brief"
CAMPAIGN_ID = "campaign_id"
EXCLUDED_PERSONA_IDS = "excluded_persona_ids"

# ── Agent outputs ─────────────────────────────────────────────────────────────
PRODUCT_PROFILE = "product_profile"
AUDIENCE_ANALYSIS = "audience_analysis"
TREND_RESEARCH = "trend_research"
CREATIVE_DIRECTIONS = "creative_directions"
SELECTED_PERSONA = "selected_persona"
IMAGE_GEN_PROMPT = "image_gen_prompt"
AB_VARIANT_PROMPT = "ab_variant_prompt"
MARKETING_OUTPUT = "marketing_output"

# ── Trend sub-pipeline intermediate keys ─────────────────────────────────────
TREND_KEYWORDS        = "trend_keywords"
YOUTUBE_TREND_DATA    = "youtube_trend_data"
TWITTER_TREND_DATA    = "twitter_trend_data"
TIKTOK_TREND_DATA     = "tiktok_trend_data"
INSTAGRAM_TREND_DATA  = "instagram_trend_data"
REDDIT_TREND_DATA     = "reddit_trend_data"
WEB_SEARCH_TREND_DATA = "web_search_trend_data"
PINTEREST_TREND_DATA  = "pinterest_trend_data"
AGGREGATED_TREND_DATA = "aggregated_trend_data"

# ── Cross-agent signals ───────────────────────────────────────────────────────
MISMATCH_FLAGS = "mismatch_flags"
PIPELINE_ERROR = "pipeline_error"

# ── All agent output keys in pipeline order ───────────────────────────────────
AGENT_OUTPUT_KEYS = [
    PRODUCT_PROFILE,
    AUDIENCE_ANALYSIS,
    TREND_RESEARCH,
    CREATIVE_DIRECTIONS,
    SELECTED_PERSONA,
    IMAGE_GEN_PROMPT,
    MARKETING_OUTPUT,
]
