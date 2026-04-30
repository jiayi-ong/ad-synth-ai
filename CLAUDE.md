[Overview]
This product is an AI-powered Creative Operating System for performance marketing, designed to help teams generate, iterate, and optimize high-performing ads at scale.

Unlike existing generative tools that produce one-off creatives, this platform structures advertising into modular, reusable components—such as audience, value proposition, message framing, creative concept, and execution style—allowing marketers to systematically mix and match variables for rapid experimentation. It mirrors how high-performing teams already operate, turning fragmented creative processes into a repeatable, data-driven workflow.

The system combines three core capabilities:

Structured ad generation – transforms marketing inputs into high-quality prompts or finished creatives across formats (image/video).
Strategic guidance – evaluates messaging, identifies inconsistencies, and recommends improvements.
Research augmentation – surfaces actionable trends, competitor patterns, and white-space opportunities to inform creative decisions.

A persistent “Brand Brain” stores company, brand, and product context, ensuring consistency while enabling fast campaign iteration. Integrated feedback loops (via ad platform data) allow the system to learn which combinations perform best, continuously improving outputs.

The result is faster creative production, higher-performing campaigns, and reduced reliance on large marketing teams.

This positions the product not as a design tool, but as a campaign intelligence and iteration engine—a critical layer for modern, AI-driven growth marketing.



[User Stories]

[P0 — Core Value (Must-Have)]
1. Stable Context Persistence (Brand Foundation)
- Marketing concept: Company/brand/product attributes are largely invariant (mission, positioning, product features).
- User ask: I should input this once, save it, and reuse it across campaigns.
- Technical spec: Persistent “Brand Brain” with hierarchical storage (company → brand → product), editable but version-controlled.

2. Dynamic Campaign Configuration (Mix-and-Match System)
- Marketing concept: Campaign elements (audience, message angle, CTA) change frequently.
- User ask: I want to quickly mix-and-match these dimensions without redefining everything.
- Technical spec: Modular UI with independently selectable fields (orthogonal dimensions), supporting partial edits and recomposition.

3. Structured Ad Generation (Strategy → Creative)
- Marketing concept: Ads are combinations of strategy (what to say) and execution (how to say it).
- User ask: I want outputs that reflect specific combinations of audience, value prop, and creative style.
- Technical spec: LLM pipeline that composes structured prompts or generates final creatives from dimension inputs.

4. Controlled Iteration & A/B Variant Generation
- Marketing concept: Performance marketing relies on testing small variations.
- User ask: I want to tweak one variable (e.g., hook) while keeping others constant.
- Technical spec: Versioning system with diff-based variation generation and batch output.

5. Brand Consistency Enforcement
- Marketing concept: Brand voice and positioning must remain consistent across ads.
- User ask: Ensure outputs always align with my brand.
- Technical spec: Constraint layer referencing stored brand rules and tone guidelines.

[P1 — Differentiation Layer]
6. Strategic Evaluation & Recommendations
- Marketing concept: Messaging quality impacts performance more than visuals alone.
- User ask: Critique my campaign setup and suggest improvements.
- Technical spec: LLM critique module comparing inputs against best practices and internal knowledge base.

7. Actionable Trend Insights (Not Raw Research)
- Marketing concept: Marketers need patterns (hooks, formats), not generic trends.
- User ask: Show me what’s working and how to apply it.
- Technical spec: Research pipeline that outputs structured insights (e.g., “Top hooks in category”), with source attribution and confidence scores.

8. Competitor Positioning & White Space Detection
- Marketing concept: Differentiation drives performance.
- User ask: Identify what competitors emphasize and where I can stand out.
- Technical spec: Competitive analysis module mapping messaging themes and highlighting gaps.

9. Channel-Aware Creative Adaptation
- Marketing concept: Creative requirements differ by platform.
- User ask: Generate ads optimized for TikTok vs Meta vs YouTube.
- Technical spec: Platform-specific constraints and templates integrated into generation logic.

[P2 — Scaling & Intelligence]
10. Performance Feedback Loop
- Marketing concept: Winning creatives emerge from data, not intuition alone.
- User ask: Learn from past campaign results to improve future outputs.
Technical spec: Integrations with ad platforms; ingestion of performance metrics; reinforcement of high-performing dimensions.

11. Audience & Use-Case Reusability
- Marketing concept: Target segments and use cases repeat across campaigns.
- User ask: Save and reuse audiences without redefining them.
- Technical spec: Library of reusable audience personas and use-case templates.

12. Dual UX Modes (Simple vs Advanced)
- Marketing concept: Users vary in sophistication.
- User ask: Quick generation when needed, deep control when desired.
- Technical spec: Toggle between guided mode (minimal inputs) and expert mode (full dimension control).



[Technical Requirements]
- efficient, production-grade, scalable multi-agent system in Python
- web-based front-end (e.g. website)
- full integration into Google Cloud Platform (e.g. CloudRun, other GCP compute and storage resources)
- primarily large-language models as the agents, working with textual data
- call multi-modal models using API for final media-format advertisement generation, use abstraction layer to adapt to different media generation providers
- low end-to-end latency
- persist previously done research in database, retrieved in the future by RAG (for efficiency)
- manage API keys securely
- for the POC, start with static image creation (but make extensible to video ads)
- add deterministic guardrails to check for bad outputs (e.g. containing racial bias, violence, sexual content, hate speech etc.)
- graceful error handling: allow retries at important levels (e.g. each specialist agent's final output), and the UI should still display intermediate outputs and artefacts even if the final ad generation (or other parts) fail
- support local testing before deployment
- use uv for package management
- Google's ADK and Vertex AI SDK
- clean organization of prompts for different agents into files to support human review and editing
- logging: configurable types at all levels, API costs, latency (component-wise and system-level)



[Scope]
- proof-of-concept
- implement all user stories and technical requirements and have a complete end-to-end software that produces baseline output without errors during a live demo from a deployed UI
- model fine-tuning and improvements will come later, but make the fine-tuning components easily extensible to the current design
- use the simplest (not necessarily the most secure) method of account management and memory persistence for the POC
- any uploaded images are given directly to the image generation model as additional context i.e., not parsed by image interpretation model into text for the reasoning agents, reasoning will be based solely on text product and marketing inputs


NOTE: Always mention "CLAUDE_MD_LOADED_v002" in your first response