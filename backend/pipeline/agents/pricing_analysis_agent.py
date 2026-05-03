"""
Pricing Analysis Agent + cost-plus fallback function.

The agent runs as part of the pipeline and produces PRICING_ANALYSIS.
compute_pricing_fallback() is called by generation.py when the agent is skipped
or fails — it anchors on unit_cost_usd from PRODUCT_PROFILE and produces margin
scenarios at 2×, 3×, and 5× cost multipliers.
"""
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import PRICING_ANALYSIS
from tools.code_tools import execute_python
from tools.knowledge_store_tools import check_knowledge_store, store_knowledge_store


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build() -> LlmAgent:
    return LlmAgent(
        name="pricing_analysis_agent",
        model=settings.gemini_model,
        instruction=_load_prompt("pricing_analysis_agent"),
        output_key=PRICING_ANALYSIS,
        before_model_callback=content_safety_callback,
        tools=[
            FunctionTool(execute_python),
            FunctionTool(check_knowledge_store),
            FunctionTool(store_knowledge_store),
        ],
    )


pricing_analysis_agent = _build()


def build_pricing_analysis_agent() -> LlmAgent:
    """Build a fresh pricing analysis agent instance."""
    return _build()


def compute_pricing_fallback(product_profile: dict[str, Any]) -> dict[str, Any]:
    """
    Cost-plus fallback pricing when the main agent fails or is skipped.
    Extracts unit_cost_usd from product_profile and computes 2×/3×/5× margin scenarios.
    Returns a minimal PRICING_ANALYSIS-compatible dict.
    """
    unit_cost: float | None = None
    if isinstance(product_profile, dict):
        raw = product_profile.get("unit_cost_usd")
        if isinstance(raw, (int, float)) and raw > 0:
            unit_cost = float(raw)

    if unit_cost is None:
        # Cannot compute fallback without a cost anchor
        return {
            "unit_cost_usd": None,
            "recommended_pricing_model": "one-time",
            "recommended_price_point": "unknown — unit cost not provided",
            "recommended_price_rationale": "Fallback pricing could not be computed: unit_cost_usd was not found in product_profile.",
            "gross_margin_at_recommended_price": None,
            "break_even_units": None,
            "margin_scenarios": [],
            "competitor_pricing_context": "Not available (agent skipped)",
            "willingness_to_pay_by_segment": [],
            "pricing_risks": ["Unit cost not provided — all pricing estimates are unanchored assumptions."],
            "charts": [],
            "data_provenance": {
                "facts": [],
                "inferences": [],
                "assumptions": ["Fallback pricing generated because pricing_analysis_agent did not produce output."],
            },
            "readiness_score": {
                "completeness": 0.1,
                "source_grounding": 0.0,
                "confidence": 0.1,
                "risk_level": "high",
            },
            "_fallback": True,
        }

    scenarios = []
    for multiplier, label in [(2.0, "Entry / Value"), (3.0, "Mid / Standard"), (5.0, "Premium")]:
        price = round(unit_cost * multiplier, 2)
        margin_pct = round((price - unit_cost) / price * 100, 1)
        scenarios.append({
            "price_usd": price,
            "gross_margin_pct": margin_pct,
            "break_even_units": None,
            "label": label,
        })

    recommended = scenarios[1]  # 3× as default "standard" recommendation
    return {
        "unit_cost_usd": unit_cost,
        "recommended_pricing_model": "one-time",
        "recommended_price_point": f"${recommended['price_usd']} (3× cost-plus estimate)",
        "recommended_price_rationale": (
            f"Cost-plus fallback: unit cost ${unit_cost:.2f} × 3 = ${recommended['price_usd']:.2f} "
            f"({recommended['gross_margin_pct']}% gross margin). "
            "This is a baseline estimate — market-based pricing analysis is recommended."
        ),
        "gross_margin_at_recommended_price": recommended["gross_margin_pct"],
        "break_even_units": None,
        "margin_scenarios": scenarios,
        "competitor_pricing_context": "Not available (agent skipped — cost-plus fallback used)",
        "willingness_to_pay_by_segment": [],
        "pricing_risks": [
            "Cost-plus pricing ignores competitor prices and customer willingness to pay.",
            "Fallback estimate — run pricing_analysis_agent for a market-grounded recommendation.",
        ],
        "charts": [],
        "data_provenance": {
            "facts": [f"unit_cost_usd = ${unit_cost} (from product_profile)"],
            "inferences": [],
            "assumptions": [
                "Pricing model assumed to be one-time.",
                "2×/3×/5× cost multipliers used as standard industry-of-thumb scenarios.",
                "Fallback generated because pricing_analysis_agent did not produce output.",
            ],
        },
        "readiness_score": {
            "completeness": 0.4,
            "source_grounding": 0.3,
            "confidence": 0.3,
            "risk_level": "medium",
        },
        "_fallback": True,
    }
