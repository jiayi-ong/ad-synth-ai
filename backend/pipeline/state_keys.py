# Contract between all pipeline agents.
# Every key used in context.state must be defined here.

# ── Inputs (set before pipeline runs) ────────────────────────────────────────
RAW_PRODUCT_DESCRIPTION = "raw_product_description"
RAW_MARKETING_BRIEF = "raw_marketing_brief"
CAMPAIGN_ID = "campaign_id"
EXCLUDED_PERSONA_IDS = "excluded_persona_ids"
BRAND_PROFILE_CONTEXT = "brand_profile_context"   # JSON of linked BrandProfile (if any)
TARGET_CHANNEL = "target_channel"                  # "meta"|"tiktok"|"youtube"|None

# ── Agent outputs ─────────────────────────────────────────────────────────────
PRODUCT_PROFILE = "product_profile"
AUDIENCE_ANALYSIS = "audience_analysis"
# Trend sub-pipeline intermediates
TREND_QUERIES = "trend_queries"
WEB_SEARCH_RESULTS = "web_search_results"
REDDIT_SEARCH_RESULTS = "reddit_search_results"
# Main agent outputs (downstream agents read these)
TREND_RESEARCH = "trend_research"
COMPETITOR_ANALYSIS = "competitor_analysis"
CREATIVE_DIRECTIONS = "creative_directions"
SELECTED_PERSONA = "selected_persona"
IMAGE_GEN_PROMPT = "image_gen_prompt"
AB_VARIANT_PROMPT = "ab_variant_prompt"
MARKETING_OUTPUT = "marketing_output"
EVALUATION_OUTPUT = "evaluation_output"
CHANNEL_ADAPTATION = "channel_adaptation"
BRAND_CONSISTENCY = "brand_consistency"

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
QUANTITATIVE_INSIGHTS = "quantitative_insights"   # numeric analysis + charts
SENTIMENT_INSIGHTS    = "sentiment_insights"       # per-source sentiment breakdown

# ── Cross-agent signals ───────────────────────────────────────────────────────
MISMATCH_FLAGS = "mismatch_flags"
PIPELINE_ERROR = "pipeline_error"
EXTRA_INPUT = "extra_input"     # Optional user context injected before a stage re-run

# ── Downstream dependency map (keys that must be cleared when a stage re-runs) ─
# Maps each state_key → list of keys to clear (inclusive of the key itself)
DOWNSTREAM_KEYS: dict[str, list[str]] = {
    PRODUCT_PROFILE:    [PRODUCT_PROFILE, AUDIENCE_ANALYSIS, TREND_RESEARCH, COMPETITOR_ANALYSIS,
                         CREATIVE_DIRECTIONS, SELECTED_PERSONA, IMAGE_GEN_PROMPT, AB_VARIANT_PROMPT,
                         MARKETING_OUTPUT, EVALUATION_OUTPUT, CHANNEL_ADAPTATION, BRAND_CONSISTENCY],
    AUDIENCE_ANALYSIS:  [AUDIENCE_ANALYSIS, TREND_RESEARCH, COMPETITOR_ANALYSIS,
                         CREATIVE_DIRECTIONS, SELECTED_PERSONA, IMAGE_GEN_PROMPT, AB_VARIANT_PROMPT,
                         MARKETING_OUTPUT, EVALUATION_OUTPUT, CHANNEL_ADAPTATION, BRAND_CONSISTENCY],
    TREND_RESEARCH:     [TREND_RESEARCH, CREATIVE_DIRECTIONS, SELECTED_PERSONA, IMAGE_GEN_PROMPT,
                         AB_VARIANT_PROMPT, MARKETING_OUTPUT, EVALUATION_OUTPUT, CHANNEL_ADAPTATION,
                         BRAND_CONSISTENCY],
    COMPETITOR_ANALYSIS:[COMPETITOR_ANALYSIS, CREATIVE_DIRECTIONS, SELECTED_PERSONA, IMAGE_GEN_PROMPT,
                         AB_VARIANT_PROMPT, MARKETING_OUTPUT, EVALUATION_OUTPUT, CHANNEL_ADAPTATION,
                         BRAND_CONSISTENCY],
    CREATIVE_DIRECTIONS:[CREATIVE_DIRECTIONS, SELECTED_PERSONA, IMAGE_GEN_PROMPT, AB_VARIANT_PROMPT,
                         MARKETING_OUTPUT, EVALUATION_OUTPUT, CHANNEL_ADAPTATION, BRAND_CONSISTENCY],
    SELECTED_PERSONA:   [SELECTED_PERSONA, IMAGE_GEN_PROMPT, AB_VARIANT_PROMPT,
                         MARKETING_OUTPUT, EVALUATION_OUTPUT, CHANNEL_ADAPTATION, BRAND_CONSISTENCY],
    IMAGE_GEN_PROMPT:   [IMAGE_GEN_PROMPT, AB_VARIANT_PROMPT,
                         MARKETING_OUTPUT, EVALUATION_OUTPUT, CHANNEL_ADAPTATION, BRAND_CONSISTENCY],
    MARKETING_OUTPUT:   [MARKETING_OUTPUT, BRAND_CONSISTENCY],
    EVALUATION_OUTPUT:  [EVALUATION_OUTPUT, BRAND_CONSISTENCY],
    CHANNEL_ADAPTATION: [CHANNEL_ADAPTATION, BRAND_CONSISTENCY],
    BRAND_CONSISTENCY:  [BRAND_CONSISTENCY],
}

# ── All agent output keys in pipeline order (for UI progress tracking) ────────
AGENT_OUTPUT_KEYS = [
    PRODUCT_PROFILE,
    AUDIENCE_ANALYSIS,
    TREND_RESEARCH,        # emitted by trend_synthesis_agent (end of TrendPipeline)
    COMPETITOR_ANALYSIS,
    CREATIVE_DIRECTIONS,
    SELECTED_PERSONA,
    IMAGE_GEN_PROMPT,
    MARKETING_OUTPUT,
    EVALUATION_OUTPUT,
    CHANNEL_ADAPTATION,
    BRAND_CONSISTENCY,
]
