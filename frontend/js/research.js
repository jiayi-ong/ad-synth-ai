import { api, getToken } from "./api.js";

export function renderResearch() {
  return `
    <div class="page">
      <h1 class="page-title">Research Hub</h1>
      <div style="display:flex;gap:24px;flex-wrap:wrap">

        <!-- Left: inputs -->
        <div style="flex:1;min-width:280px">
          <div class="card">
            <div class="card-title mb-8">New Research Run</div>
            <form id="research-form">
              <div class="form-group">
                <label>Product / Category *</label>
                <input id="r-product" required placeholder="Running shoes for urban athletes" />
              </div>
              <div class="form-group">
                <label>Target Audience</label>
                <input id="r-audience" placeholder="Professionals aged 25-40" />
              </div>
              <div class="form-group">
                <label>Research Type</label>
                <select id="r-type">
                  <option value="both">Trends + Competitors</option>
                  <option value="trends">Trends Only</option>
                  <option value="competitors">Competitors Only</option>
                </select>
              </div>
              <div class="form-group">
                <label class="checkbox-label" style="text-transform:none;letter-spacing:0">
                  <input type="checkbox" id="r-force" style="width:auto" />
                  Force refresh (bypass cache)
                </label>
              </div>
              <button type="submit" class="btn btn-primary" id="r-btn" style="width:100%;justify-content:center">
                Run Research
              </button>
              <div class="error-msg" id="r-error"></div>
            </form>
          </div>

          <!-- Progress -->
          <div id="r-progress-wrap" style="display:none;margin-top:8px">
            <div class="progress-bar-wrap">
              <div class="progress-bar-fill" id="r-progress-bar" style="width:0%"></div>
            </div>
            <div id="r-status-text" class="text-muted" style="font-size:12px;text-align:center;margin-top:4px"></div>
          </div>
        </div>

        <!-- Right: results stream + history -->
        <div style="flex:1.5;min-width:300px">
          <div id="r-results" style="display:none">
            <div class="card">
              <div class="card-title mb-8">Results</div>
              <div id="r-result-body"></div>
            </div>
          </div>

          <div id="r-history-wrap">
            <div class="section-header">
              <div class="section-title">Recent Research</div>
            </div>
            <div id="r-history"><div class="text-muted" style="font-size:13px">Loading…</div></div>
          </div>
        </div>
      </div>
    </div>
  `;
}

export function bindResearch() {
  loadHistory();

  document.getElementById("research-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("r-btn");
    btn.disabled = true;
    document.getElementById("r-error").textContent = "";
    document.getElementById("r-progress-wrap").style.display = "block";
    document.getElementById("r-results").style.display = "none";
    document.getElementById("r-progress-bar").style.width = "0%";
    document.getElementById("r-status-text").textContent = "Starting…";

    const payload = {
      product_description: document.getElementById("r-product").value.trim(),
      target_audience: document.getElementById("r-audience").value.trim() || null,
      research_type: document.getElementById("r-type").value,
      force_refresh: document.getElementById("r-force").checked,
    };

    startResearchSSE(payload);
  });
}

function startResearchSSE(payload) {
  const token = getToken();
  fetch("/research", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
    body: JSON.stringify(payload),
  }).then(res => {
    if (!res.ok) throw new Error("Research request failed");
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let progress = 0;

    function readChunk() {
      reader.read().then(({ done, value }) => {
        if (done) return;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const evt = JSON.parse(line.slice(6));
              handleResearchEvent(evt, payload.research_type);
              if (evt.event === "agent_complete") progress++;
              const total = payload.research_type === "both" ? 6 : 3;
              document.getElementById("r-progress-bar").style.width = Math.min(100, Math.round(progress / total * 100)) + "%";
            } catch {}
          }
        }
        readChunk();
      }).catch(err => {
        document.getElementById("r-error").textContent = "Stream error: " + err.message;
        document.getElementById("r-btn").disabled = false;
      });
    }
    readChunk();
  }).catch(err => {
    document.getElementById("r-error").textContent = err.message;
    document.getElementById("r-btn").disabled = false;
  });
}

function handleResearchEvent(evt) {
  const { event, agent, data } = evt;

  if (event === "started") {
    document.getElementById("r-status-text").textContent = "Research pipeline running…";
  }

  if (event === "agent_complete") {
    document.getElementById("r-status-text").textContent = `Completed: ${(agent || "").replace(/_/g, " ")}`;
    showResult(agent, data);
  }

  if (event === "done") {
    document.getElementById("r-status-text").textContent = "Research complete!";
    document.getElementById("r-progress-bar").style.width = "100%";
    document.getElementById("r-btn").disabled = false;
    loadHistory();
  }

  if (event === "error") {
    document.getElementById("r-error").textContent = data?.message || "Research failed";
    document.getElementById("r-btn").disabled = false;
  }
}

function showResult(agent, data) {
  const wrap = document.getElementById("r-results");
  const body = document.getElementById("r-result-body");
  wrap.style.display = "block";

  const label = (agent || "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  const pre = document.createElement("div");
  pre.style.marginBottom = "12px";
  pre.innerHTML = `
    <div class="text-muted" style="font-size:11px;margin-bottom:4px">${label}</div>
    <pre style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:12px;font-size:11px;white-space:pre-wrap;word-break:break-word;color:var(--text-muted)">${JSON.stringify(data, null, 2)}</pre>
  `;
  body.appendChild(pre);
}

async function loadHistory() {
  const wrap = document.getElementById("r-history");
  if (!wrap) return;
  try {
    const items = await api.getResearchHistory();
    if (!items.length) {
      wrap.innerHTML = `<div class="empty-state"><p>No research history yet.</p></div>`;
      return;
    }
    wrap.innerHTML = items.map(item => `
      <div class="card" style="cursor:default">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <div class="card-title" style="font-size:13px">${esc(item.query_text || item.query_type)}</div>
            <div class="card-meta">${item.query_type} · ${fmt(item.created_at)} ${item.cache_hit ? "· cache hit" : ""}</div>
          </div>
          <span class="badge badge-success">Done</span>
        </div>
      </div>
    `).join("");
  } catch {
    wrap.innerHTML = `<div class="text-muted" style="font-size:13px">Could not load history.</div>`;
  }
}

function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
function fmt(dt) { return new Date(dt).toLocaleDateString(); }
