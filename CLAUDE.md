[Overview]
You are an expert in building production-grade, scalable, and impactful software systems for applications in marketing. You are a computer scientist by training, with knowledge in the latest concepts and fundamentals in software systems engineering and design, large language models, and full-stack development. Synthesize the following ideas into one coherent, complete, and high-value software proof-of-concept. Focus on maximizing novelty and business value as this will be pitched to a board of angel investors, while balancing technical correctness, complexity, and efficiency.



[Software Overview]
A web-based multi-agent platform that turns a product image, product description, and marketing brief into investor-grade ad concepts and a production-ready prompt for static image ad generation. The system acts as the “marketing brain.” The final text-to-media model that generates the ad receives only clean creative instructions, not strategy clutter.



[User Stories / Features]
- main idea: a multi-agent system that (1) takes images of a single product, textual product descriptions, marketing inputs like target audience, value proposition, positioning, branding (and other relevant marketing inputs) (2) combines research about the latest related trends from the internet (many different sources, e.g. instagram, tiktok, reddit, google search, X) (3) distill and synthesize a plan (4) and finally outputs a detailed text prompt for a text-to-media model to generate an advertisement

- the prompt must omit clunky context, as the agentic system needs to be the brain that produces the text design of the ad, and the ad creation model just needs to design info to create it (separation of concerns)

- output other useful marketing recommendations, strategy, and advice - like product slogan, how it fits into the overall brand, competitors, product differentiators, legal/compliance concerns

- target users: marketing team at a company or small/individual product creators

- advanced feature: persistent AI personas that affect (language, tone, belief, style, physical and facial features) - efficiently persist previously generated personas (text descriptions and media) that the human user can selectively include / exclude for each new ad generation

- advanced feature: critically assess the given and researched data to identify potential mismatches (or affirm correctness) between actual product attributes and intended audience or current trends, and recommend a few improvements or alternatives

- advanced feature: generate a control and variant ad for A/B testing - after generating the first ad, submit a new follow-up prompt with only the instructions to modify one key element of the first ad



[Agentic Design]
- Deterministic multi-stage agent pipeline (planner → specialist agents → synthesizer), using agent-as-tools, with targeted routing nodes and a final critique/validation layer

[Agent 1]: Product Understanding Agent
- Purpose: interpret the uploaded product image and text.
Responsibilities:
- Given text description of product, identify product type, visual attributes, colors, materials, style, likely use cases
- Extract claims from description
- Detect ambiguity or inconsistencies
- Generate structured product profile

[Agent 2]: Audience & Positioning Agent
- Purpose: translate marketing inputs into a clear strategic direction.
Responsibilities:
- Define primary and secondary audiences
- Identify pain points, desires, objections
- Recommend positioning
- Match tone and creative style to audience
- Detect product-audience mismatch

[Agent 3]: Trend Research Agent
- Purpose: gather current cultural and marketing signals.
Sources for scalable version:
Google Search
Reddit
TikTok trend APIs or scraping partner
Instagram trend data
X/Twitter
YouTube Shorts
Pinterest
Amazon reviews
Competitor websites
Meta Ad Library
Google Trends

POC implementation:
- Use search APIs and limited public web sources
- Store retrieved snippets
- Summarize only relevant trends
- Avoid making unsupported claims

[Agent 4]: Creative Strategy Agent
- Purpose: synthesize product, audience, and trend research into campaign concepts.
Responsibilities:
- Generate 3–5 creative directions
- Score each by novelty, audience fit, conversion potential, brand fit
- Recommend best concept
- Produce slogan, CTA, and supporting copy

Example concepts:
- Performance Hero Shot
- Lifestyle Confidence Ad
- Social Proof / Trend-Led Ad
- Founder/Product Origin Story
- Before-and-After Problem Solver

[Agent 5]: Persona Agent
- Purpose: manage reusable AI personas.
A persona includes:
Name
Demographic traits
Physical appearance
Facial style
Fashion style
Voice and tone
Beliefs/values
Brand association
Prior generated media references
Usage history
Exclusion rules

[Agent 6]: Prompt Engineering Agent
Purpose: create the final clean prompt for the image-generation model.
This agent removes strategic clutter and produces only execution-ready creative instructions.
Prompt structure:
```
[General Description]
A premium static image advertisement for a lightweight urban running shoe.

[Product Placement]
The shoe is centered in the foreground, angled slightly to the right, with the sole visible.

[Scene]
Modern urban running track at sunrise, soft golden light, clean background, energetic but premium atmosphere.

[Human Model Traits]
Athletic woman in her late 20s, confident expression, wearing minimalist black running apparel.

[Human Model Actions]
She is kneeling beside the shoe, one hand resting near it, looking directly at the camera with a subtle smile.

[Brand Style]
Clean, bold, high-performance, modern, aspirational.

[Color Palette]
White, black, neon green accents, warm sunrise highlights.

[Text Injection 1]
Insert the slogan "Run Lighter. Go Further." at the bottom-center in bold modern sans-serif typography.

[Text Injection 2]
Insert "Ultra-light cushioning for everyday speed" below the slogan in smaller text.

[Composition]
Vertical 4:5 Instagram ad composition, product highly visible, ample negative space for text.

[Lighting]
Soft cinematic lighting with realistic shadows.

[Quality]
Photorealistic commercial advertising image, sharp focus, high-resolution, premium product photography.

[Negative Instructions]
No distorted shoe shape, no extra logos, no unreadable text, no unrealistic anatomy, no cluttered background.
```

[Agent 7]: Marketing Recommendation Agent
Purpose: provide extra strategic output beyond the ad prompt.
Outputs:
Product slogan
CTA
Brand alignment notes
Audience fit analysis
Suggested campaign angle
Suggested platforms
Ad copy variants
Landing page headline
Email subject line
Social caption
Risks and improvement recommendations



[Technical Requirements]
- efficient, production-grade, scalable multi-agent system in Python
- web-based front-end (e.g. website)
- full integration into Google Cloud Platform (e.g. CloudRun, other GCP compute and storage resources)
- primarily large-language models as the synthesis agents
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


[User Interface]
Optimize the UI design to accomodate all the following factors:
Login page: enter credentials and log in
Key abstract classes: (1) Campaign (2) Persona (3) Product (4) Advertisement
Main page: 
- create a new campaign or load existing one - defines the campaign-level details like mission, values, brand etc.
- once a campaign is selected / created, create or load a project: project encompasses different saved personas and products, and previously generated advertisements
- products encompasses the product images and descriptions
- modularized personas, products to support mixing different combinations for a campaign
- once all necessary information is gathered, click generate and display final result
Specialized tabs: one for each agent to see intermediate reasoning and outputs/artefacts for full transparency



[Scope for the POC]
- implement all listed features and technical requirements and have a complete end-to-end software that produces baseline output without errors during a live demo from a deployed UI
- model fine-tuning and improvements will come later, but make the fine-tuning components easily extensible to the current design
- use the simplest (not necessarily the most secure) method of account management and memory persistence for the POC
- any uploaded images are given directly to the image generation model as additional context i.e., not parsed by image interpretation model into text for the reasoning agents, reasoning will be based solely on text product and marketing inputs



NOTE: Always mention "CLAUDE_MD_LOADED" in your first response