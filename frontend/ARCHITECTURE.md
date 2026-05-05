# Frontend Architecture

The frontend is a vanilla HTML/CSS/ES6 single-page application with no build step, bundler, or framework. It communicates with the FastAPI backend via REST endpoints and SSE streams.

## Files

```
frontend/
├── index.html          # Single HTML entry point — all pages rendered inside <div id="app">
├── css/
│   ├── styles.css      # All styling — responsive, component classes
│   └── chatbot.css     # Chatbot widget styles (reuses CSS variables from styles.css)
└── js/
    ├── app.js          # Hash router, expert mode toggle, auth token check on load
    ├── api.js          # HTTP client wrapper (fetch + JWT auth headers, all endpoint methods)
    ├── auth.js         # Login and register page rendering + form handlers
    ├── campaigns.js    # Campaign list page and create campaign modal
    ├── project.js      # Campaign detail page (products + unit_cost_usd, personas, run generation)
    ├── generate.js     # Ad generation form, SSE streaming handler, result display
    ├── agent_tabs.js   # 16-tab agent output panel with per-stage rerun support
    ├── stage_renderers.js  # Structured HTML renderers for each agent's JSON output
    ├── brands.js       # Brand Brain — brand profile list and editor
    ├── research.js     # Research Hub — cached trend data display
    ├── library.js      # Ad Library — past advertisement results
    └── chatbot.js      # AI Assistant chatbox widget (injected outside #app, persists across routes)
```

## Routing

The app uses hash-based routing — no server-side routing needed. `app.js` listens for `hashchange` events and calls the appropriate render function.

| Hash Route | Page | Module |
|------------|------|--------|
| `#login` | Login form | `auth.js` |
| `#register` | Registration form | `auth.js` |
| `#campaigns` | Campaign list | `campaigns.js` |
| `#project/:campaignId` | Campaign detail | `project.js` |
| `#brands` | Brand profile list | `brands.js` |
| `#brands/:brandId` | Brand profile editor | `brands.js` |
| `#generate/:campaignId/:adId?` | Ad generation | `generate.js` |
| `#research` | Research Hub | `research.js` |
| `#library` | Ad Library | `library.js` |

On page load, `app.js` checks for a valid JWT in `localStorage`. If absent or expired, it redirects to `#login`.

## API Client (`api.js`)

All backend calls go through a single `api.js` module that:
- Attaches `Authorization: Bearer <token>` to every request
- Parses JSON responses and throws on non-2xx status
- Provides typed methods for every endpoint (e.g., `api.getCampaigns()`, `api.createProduct(data)`)
- Handles 401 responses by clearing the token and redirecting to `#login`

## Ad Generation Flow (`generate.js`)

The generation page is the most complex part of the frontend:

1. User fills in the generation form (target audience, value prop, positioning, tone, channel, personas to include/exclude)
2. On submit — calls `POST /generate` which returns an SSE stream
3. An `EventSource`-like SSE reader (built on `fetch` + `ReadableStream`) parses each `data: {...}` event
4. As events arrive:
   - `started` → shows the pipeline progress bar
   - `agent_start` → marks that agent's tab as loading
   - `agent_complete` → updates progress bar, stores agent output, triggers `updateAgentTab(agent, data)` in `agent_tabs.js`; loop agents (market_segmentation, audience_analysis) may fire multiple times — each updates the tab content but the progress bar only advances on the first completion
   - `image_generating` → shows spinner with provider name
   - `image_ready` → displays generated ad image and A/B variant
   - `cost_summary` → shows token count + estimated USD cost
   - `done` → hides progress bar, enables post-generation actions
   - `error` → shows inline error message; partial results remain visible

## Agent Output Tabs (`agent_tabs.js`)

Defines the ordered list of 16 pipeline tabs and manages the tab panel UI. Key exports:

### `AGENTS` Array (pipeline order)

```javascript
export const AGENTS = [
  { key: "product_profile",       short: "Product",     icon: "📦" },
  { key: "market_segmentation",   short: "Segments",    icon: "📊" },
  { key: "audience_analysis",     short: "Audience",    icon: "🎯" },
  { key: "trend_research",        short: "Trends",      icon: "📈" },
  { key: "competitor_analysis",   short: "Competitors", icon: "🔍" },
  { key: "pricing_analysis",      short: "Pricing",     icon: "💰" },
  { key: "creative_directions",   short: "Creative",    icon: "💡" },
  { key: "selected_persona",      short: "Persona",     icon: "👤" },
  { key: "image_gen_prompt",      short: "Prompts",     icon: "✍️"  },
  { key: "campaign_architecture", short: "Campaign",    icon: "🗺️"  },
  { key: "experiment_design",     short: "Experiments", icon: "🧪" },
  { key: "marketing_output",      short: "Marketing",   icon: "📣" },
  { key: "evaluation_output",     short: "Evaluation",  icon: "⭐" },
  { key: "channel_adaptation",    short: "Channel",     icon: "📱" },
  { key: "brand_consistency",     short: "Brand",       icon: "🛡️"  },
  { key: "image_generation",      short: "Image Gen",   icon: "🖼️"  },
];
```

### Downstream Key Map

`DOWNSTREAM_KEYS` is a JS mirror of `state_keys.py`'s `DOWNSTREAM_KEYS` dict. Used by the stage rerun UI to clear the correct downstream tabs before re-running. Both `_getDownstreamNames()` (header-click rerun) and `_startRerun()` reference this map.

### Stage Rerun

Each tab header has a rerun button that calls `POST /generate/{adId}/rerun-stage`. Before submitting, it clears the downstream tabs and shows them in loading state. Stages can also inject `extra_input` context before re-running.

## Stage Renderers (`stage_renderers.js`)

Renders structured HTML from each agent's parsed JSON output. The main entry point:

```javascript
export function renderStageData(key, data) { ... }
```

**Fallback chain:**
1. If `data` is null or has `data.error` → shows "No data" message
2. If `data` is a string (JSON parse failed on backend) → shows raw content with a `⚠️ Raw agent output` warning
3. Dispatches to the per-key renderer via `_dispatchRender(key, data)`
4. If the rendered HTML is empty (all fields missing) → falls back to `renderFallback(data)` with a `⚠️ Agent output empty or unexpected structure` warning

**Per-key renderers:**

| Renderer | Key | Highlights |
|----------|-----|-----------|
| `renderProductProfile` | `product_profile` | quality tier, features, compliance flags, readiness score |
| `renderMarketSegmentation` | `market_segmentation` | segment table (TAM/SAM/attractiveness), charts, readiness score |
| `renderAudienceAnalysis` | `audience_analysis` | demographics, pain points, mismatch flags (handles both string and object format), readiness score |
| `renderTrendResearch` | `trend_research` | summary, charts, hooks, visual signals, trend cards with sources |
| `renderCompetitorAnalysis` | `competitor_analysis` | differentiation, competitor themes, whitespace opportunities, readiness score |
| `renderPricingAnalysis` | `pricing_analysis` | recommended price + model, break-even units, margin scenario table, charts, readiness score |
| `renderCreativeDirections` | `creative_directions` | scored concept cards (novelty/fit/conversion/brand), recommended concept highlighted, readiness score |
| `renderPersona` | `selected_persona` | persona card with traits |
| `renderImageGenPrompt` | `image_gen_prompt` | primary prompt + A/B variant |
| `renderCampaignArchitecture` | `campaign_architecture` | phased timeline, budget allocation donut, success metrics, readiness score |
| `renderExperimentDesign` | `experiment_design` | experiment cards (hypothesis, sample size, power, MDE), power curve chart, readiness score |
| `renderMarketingOutput` | `marketing_output` | recommendations, readiness score |
| `renderEvaluationOutput` | `evaluation_output` | scores, assessment, readiness score |
| `renderChannelAdaptation` | `channel_adaptation` | platform-specific creative breakdown |
| `renderBrandConsistency` | `brand_consistency` | consistency score, flags, readiness score |
| `renderImageGeneration` | `image_generation` | generated image + A/B variant |

**Shared helpers:**
- `renderCharts(charts)` — renders `charts` array as base64 `<img>` tags with title and description captions
- `renderReadinessScore(rs)` — 2×2 grid: completeness %, source grounding %, confidence %, risk level badge

## Product Form (`project.js`)

The product create and edit forms include a `unit_cost_usd` number input (step 0.01). This value is passed to the API and stored on the `Product` record. It is displayed in the product card as "Unit Cost: $X.XX" when set. The pipeline uses it as the cost anchor for the pricing fallback model.

## Expert Mode

A toggle in the nav bar switches between:
- **Simple mode** — shows the final generated ad, marketing recommendations, and evaluation score
- **Expert mode** — shows all 16 agent output tabs, intermediate pipeline data, and token cost breakdown

The setting is persisted in `localStorage` so it survives page reloads.

## State Management

There is no global state manager. Each page module manages its own local state within its render/event handler scope. Shared state (auth token, expert mode preference) is stored in `localStorage`.

## Auth Flow

```
localStorage.getItem('token')
    ├── null / expired → redirect to #login
    └── valid → proceed to requested route

POST /auth/login → { token }
    └── localStorage.setItem('token', token)

Logout → localStorage.removeItem('token') → redirect to #login
```

## Chatbot Widget (`chatbot.js`)

The chatbot assistant is a persistent floating widget injected directly into `document.body` (not into `#app`). This means it survives all hash route changes and is always accessible when logged in.

Key design points:
- **DOM injection**: `DOMContentLoaded` → `injectWidget()` appends `<div id="chatbot-widget">` to `document.body`
- **Visibility**: Hidden on `#login` and `#register` pages; shown on all authenticated routes
- **Session ID**: Persisted in `localStorage['chatbot_session_id']`, initialized on first panel open via `POST /chat/session`
- **Advertisement context**: On each message send, `window.location.hash` is parsed with `/#generate\/[^/]+\/([a-f0-9-]{36})/` to detect if the user is viewing a specific ad generation result. If so, `advertisement_id` is sent with the message and the backend injects pipeline context into the system prompt.
- **SSE streaming**: Uses `fetch` + `ReadableStream` (same pattern as `generate.js`), appending tokens to the assistant bubble in real time
- **Guardrail responses**: Delivered as normal SSE token streams — no special frontend handling needed

## Adding a New Page

1. Add a `<script src="js/mypage.js"></script>` in `index.html`
2. Export a `renderMyPage(params)` function from `mypage.js`
3. Add a route entry in `app.js`'s router switch
4. Add a nav link in `index.html` (visible only when logged in)

## Adding a New Agent Tab

1. Add an entry to the `AGENTS` array in `agent_tabs.js` in pipeline order
2. Add the downstream chain for that key in both `_getDownstreamNames()` and `_startRerun()`'s map (mirrors `DOWNSTREAM_KEYS` in `state_keys.py`)
3. Add a `case "my_key": return renderMyAgent(data);` to `_dispatchRender()` in `stage_renderers.js`
4. Implement `renderMyAgent(d)` returning an HTML string
