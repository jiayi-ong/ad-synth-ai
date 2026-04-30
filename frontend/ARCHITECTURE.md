# Frontend Architecture

The frontend is a vanilla HTML/CSS/ES6 single-page application with no build step, bundler, or framework. It communicates with the FastAPI backend via REST endpoints and SSE streams.

## Files

```
frontend/
├── index.html          # Single HTML entry point — all pages rendered inside <div id="app">
├── css/
│   └── styles.css      # All styling — dark theme, responsive, component classes
└── js/
    ├── app.js          # Hash router, expert mode toggle, auth token check on load
    ├── api.js          # HTTP client wrapper (fetch + JWT auth headers, all endpoint methods)
    ├── auth.js         # Login and register page rendering + form handlers
    ├── campaigns.js    # Campaign list page and create campaign modal
    ├── project.js      # Campaign detail page (products, personas, run generation)
    ├── generate.js     # Ad generation form, SSE streaming handler, result display
    ├── agent_tabs.js   # Collapsible agent output tabs (rendered after generation)
    ├── brands.js       # Brand Brain — brand profile list and editor
    ├── research.js     # Research Hub — cached trend data display
    └── library.js      # Ad Library — past advertisement results
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

1. User fills in the generation form (target audience, value prop, tone, channel, personas to include/exclude)
2. On submit — calls `POST /generate` which returns an SSE stream
3. An `EventSource`-like SSE reader (built on `fetch` + `ReadableStream`) parses each `data: {...}` event
4. As events arrive:
   - `started` → shows the pipeline progress bar
   - `agent_complete` → updates progress, stores agent output, triggers tab render in `agent_tabs.js`
   - `image_generating` → shows spinner with provider name
   - `image_ready` → displays generated ad image and A/B variant
   - `cost_estimate` → shows token count + estimated USD cost
   - `done` → hides progress bar, enables "Save" and "Download" buttons
   - `error` → shows inline error message; partial results remain visible

## Agent Output Tabs (`agent_tabs.js`)

After generation completes, each agent's JSON output is displayed in a collapsible tab panel. `agent_tabs.js`:
- Receives the ordered list of `(agentName, output)` pairs from `generate.js`
- Renders a tab per agent with a human-readable label
- Pretty-prints the JSON output with syntax highlighting
- Expert mode (toggle in nav bar, stored in `localStorage`) shows all intermediate agent outputs including trend sub-pipeline steps

## Expert Mode

A toggle in the nav bar switches between:
- **Simple mode** — shows only the final generated ad, marketing recommendations, and evaluation score
- **Expert mode** — shows all 11 agent output tabs, raw pipeline state, trend sub-pipeline intermediate outputs, and token cost breakdown

The setting is persisted in `localStorage` so it survives page reloads.

## State Management

There is no global state manager. Each page module (`campaigns.js`, `generate.js`, etc.) manages its own local state within its render/event handler scope. Shared state (auth token, expert mode preference) is stored in `localStorage`.

## Auth Flow

```
localStorage.getItem('token')
    ├── null / expired → redirect to #login
    └── valid → proceed to requested route

POST /auth/login → { token }
    └── localStorage.setItem('token', token)

Logout → localStorage.removeItem('token') → redirect to #login
```

## Adding a New Page

1. Add a `<script src="js/mypage.js"></script>` in `index.html`
2. Export a `renderMyPage(params)` function from `mypage.js`
3. Add a route entry in `app.js`'s router switch
4. Add a nav link in `index.html` (visible only when logged in)
