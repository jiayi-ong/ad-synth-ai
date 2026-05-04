from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types as genai_types

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import EXPERIMENT_DESIGN
from tools.code_tools import execute_python

_NO_THINKING = genai_types.GenerateContentConfig(
    thinking_config=genai_types.ThinkingConfig(thinking_budget=0)
)


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build() -> LlmAgent:
    return LlmAgent(
        name="experiment_design_agent",
        model=settings.gemini_model,
        include_contents='none',
        instruction=_load_prompt("experiment_design_agent"),
        output_key=EXPERIMENT_DESIGN,
        generate_content_config=_NO_THINKING,
        before_model_callback=content_safety_callback,
        tools=[FunctionTool(execute_python)],
    )


experiment_design_agent = _build()


def build_experiment_design_agent() -> LlmAgent:
    """Build a fresh experiment design agent instance."""
    return _build()


def compute_experiment_design_fallback() -> dict:
    """
    Deterministic fallback experiment design when the agent fails at high context.
    Uses scipy to compute real sample sizes (no LLM required).
    Returns a minimal EXPERIMENT_DESIGN-compatible dict.
    """
    try:
        import math
        from scipy import stats
        import numpy as np

        def _sample_size(baseline: float, mde: float, alpha: float = 0.05, power: float = 0.80) -> int:
            p1, p2 = baseline, baseline + mde
            z_a = stats.norm.ppf(1 - alpha / 2)
            z_b = stats.norm.ppf(power)
            pooled = (p1 + p2) / 2
            n = ((z_a * math.sqrt(2 * pooled * (1 - pooled)) +
                  z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (mde ** 2)
            return int(math.ceil(n))

        experiments = [
            {
                "name": "Hook Copy A/B Test",
                "hypothesis": "If we change the ad hook from benefit-led to problem-led, CTR will improve by 0.6pp",
                "control": "Benefit-led hook: 'Fuel your day with 50+ superfoods'",
                "variant": "Problem-led hook: 'Tired by 2pm? This fixes that'",
                "primary_metric": "CTR",
                "baseline_rate_assumption": "3% CTR (DTC supplement category benchmark — ASSUMPTION)",
                "minimum_detectable_effect_pct": 0.6,
                "significance_level": 0.05,
                "statistical_power": 0.80,
                "sample_size_per_arm": _sample_size(0.03, 0.006),
                "estimated_duration_days": 14,
                "ice_score": {"impact": 4, "confidence": 4, "ease": 5, "total": 80.0},
                "priority": "high",
            },
            {
                "name": "CTA Button Text Test",
                "hypothesis": "If we change CTA from 'Shop Now' to 'Try Risk-Free', conversion rate will improve by 1pp",
                "control": "'Shop Now' CTA button",
                "variant": "'Try Risk-Free' CTA button",
                "primary_metric": "conversion_rate",
                "baseline_rate_assumption": "4% conversion rate (DTC landing page benchmark — ASSUMPTION)",
                "minimum_detectable_effect_pct": 1.0,
                "significance_level": 0.05,
                "statistical_power": 0.80,
                "sample_size_per_arm": _sample_size(0.04, 0.01),
                "estimated_duration_days": 21,
                "ice_score": {"impact": 4, "confidence": 3, "ease": 5, "total": 60.0},
                "priority": "high",
            },
            {
                "name": "Audience Segment Targeting Test",
                "hypothesis": "If we target fitness-oriented professionals vs. general wellness audience, ROAS will improve by 20%",
                "control": "Broad wellness audience targeting",
                "variant": "Narrowed fitness-professional interest targeting",
                "primary_metric": "ROAS",
                "baseline_rate_assumption": "2.5× ROAS (DTC supplement paid social benchmark — ASSUMPTION)",
                "minimum_detectable_effect_pct": 0.5,
                "significance_level": 0.05,
                "statistical_power": 0.80,
                "sample_size_per_arm": _sample_size(0.025, 0.005),
                "estimated_duration_days": 28,
                "ice_score": {"impact": 5, "confidence": 3, "ease": 3, "total": 45.0},
                "priority": "high",
            },
        ]
        computed = True
    except Exception:
        # scipy unavailable — use hardcoded estimates
        experiments = [
            {
                "name": "Hook Copy A/B Test",
                "hypothesis": "If we change the ad hook from benefit-led to problem-led, CTR will improve by 0.6pp",
                "control": "Benefit-led hook",
                "variant": "Problem-led hook",
                "primary_metric": "CTR",
                "baseline_rate_assumption": "3% CTR (DTC benchmark — ASSUMPTION)",
                "minimum_detectable_effect_pct": 0.6,
                "significance_level": 0.05,
                "statistical_power": 0.80,
                "sample_size_per_arm": 3842,
                "estimated_duration_days": 14,
                "ice_score": {"impact": 4, "confidence": 4, "ease": 5, "total": 80.0},
                "priority": "high",
            },
        ]
        computed = False

    return {
        "experiments": experiments,
        "prioritization_rationale": (
            "Hook copy tests highest priority: fast to run, directly impacts top-of-funnel CTR, "
            "and copy changes are low-cost to implement. CTA test second: high conversion leverage "
            "at low implementation cost. Audience targeting third: highest potential ROAS impact "
            "but requires longer duration and more budget."
            + (" (Fallback — experiment_design_agent did not produce output.)" if not computed else
               " (Fallback — sample sizes computed with scipy.)")
        ),
        "charts": [
            {
                "title": "Power Curve: Hook Copy A/B Test",
                "description": "Statistical power vs. sample size per arm for the hook copy experiment",
                "image_base64": None,
            }
        ],
        "data_provenance": {
            "facts": [],
            "inferences": [],
            "assumptions": [
                "3% CTR baseline from DTC supplement category benchmarks.",
                "4% landing page conversion rate from DTC benchmarks.",
                "2.5× ROAS baseline from paid social DTC benchmarks.",
                "Fallback generated because experiment_design_agent did not produce output.",
            ],
        },
        "readiness_score": {
            "completeness": 0.5,
            "source_grounding": 0.2,
            "confidence": 0.4,
            "risk_level": "medium",
        },
        "_fallback": True,
    }
