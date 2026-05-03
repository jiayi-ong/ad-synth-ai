"""
Positioning ↔ Segmentation feedback loop.

Wraps market_segmentation_agent, audience_positioning_agent, and loop_evaluator_agent
in an ADK LoopAgent (max 3 iterations). The evaluator calls exit_loop() when
positioning and segmentation have sufficiently converged (convergence_score >= 0.80).
If 3 iterations complete without convergence the loop terminates automatically,
passing through whatever state was last written.

Each iteration: market_segmentation writes MARKET_SEGMENTATION → audience_positioning
reads it and writes AUDIENCE_ANALYSIS → loop_evaluator reads both, writes
LOOP_EVAL_SIGNAL, and optionally writes feedback into LOOP_FEEDBACK for the next
market_segmentation iteration.
"""
from google.adk.agents import LoopAgent, SequentialAgent

from backend.pipeline.agents.audience_agent import build_audience_agent
from backend.pipeline.agents.loop_evaluator_agent import build_loop_evaluator_agent
from backend.pipeline.agents.market_segmentation_agent import build_market_segmentation_agent


def build_positioning_segmentation_loop() -> LoopAgent:
    """
    Build a fresh LoopAgent instance containing fresh sub-agent instances.
    ADK requires that agents inside a LoopAgent be unparented (not already
    attached to a pipeline), so we always use the build_* factory functions.
    """
    loop_body = SequentialAgent(
        name="loop_body",
        sub_agents=[
            build_market_segmentation_agent(),
            build_audience_agent(),
            build_loop_evaluator_agent(),
        ],
    )
    return LoopAgent(
        name="positioning_segmentation_loop",
        max_iterations=3,
        sub_agents=[loop_body],
    )


# Module-level instance used by orchestrator
positioning_segmentation_loop = build_positioning_segmentation_loop()
