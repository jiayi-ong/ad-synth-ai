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
              // trends pipeline: query+search(2) + quant + sentiment + synthesis + validator = 6
              // both: trends(6) + competitor(1) = 7
              const total = payload.research_type === "both" ? 7 : payload.research_type === "competitors" ? 1 : 6;
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

// ── Research result renderers ─────────────────────────────────────────────────

function showResult(agent, data) {
  const wrap = document.getElementById("r-results");
  const body = document.getElementById("r-result-body");
  wrap.style.display = "block";

  const section = document.createElement("div");
  section.style.marginBottom = "20px";

  const agentLabel = (agent || "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

  let innerHtml = "";
  if (agent === "trend_research") {
    innerHtml = renderTrendResult(agentLabel, data);
  } else if (agent === "quantitative_insights") {
    innerHtml = renderQuantitativeResult(agentLabel, data);
  } else if (agent === "sentiment_insights") {
    innerHtml = renderSentimentResult(agentLabel, data);
  } else if (agent === "competitor_analysis") {
    innerHtml = renderCompetitorResult(agentLabel, data);
  } else {
    innerHtml = renderGenericResult(agentLabel, data);
  }

  section.innerHTML = innerHtml;
  body.appendChild(section);
}

function renderSources(sources) {
  if (!Array.isArray(sources) || !sources.length) return "";
  const links = sources
    .filter(s => s && s.url)
    .map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:underline;font-size:11px;margin-right:8px">${esc(s.label || s.url)}</a>`)
    .join("");
  return links ? `<div style="margin-top:4px">${links}</div>` : "";
}

function renderTrendResult(label, data) {
  const trends = data?.trends || [];
  const hooks = data?.recommended_hooks || [];
  const aesthetics = data?.visual_aesthetic_signals || [];
  const validationLog = data?.validation_log || [];

  const trendsHtml = trends.map(t => `
    <div style="border:1px solid var(--border);border-radius:6px;padding:10px;margin-bottom:8px">
      <div style="font-weight:600;font-size:13px;margin-bottom:2px">${esc(t.trend_name)}</div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:4px">${esc(t.description)}</div>
      <div style="font-size:11px;margin-bottom:4px"><span style="color:var(--text-muted)">Relevance:</span> ${esc(t.relevance)}</div>
      ${(t.platforms || []).map(p => `<span style="display:inline-block;background:var(--surface2);border-radius:4px;padding:1px 6px;font-size:10px;margin-right:4px">${esc(p)}</span>`).join("")}
      ${t.evidence ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;font-style:italic">${esc(t.evidence)}</div>` : ""}
      ${renderSources(t.sources)}
    </div>
  `).join("");

  const hooksHtml = hooks.length ? `
    <div style="margin-top:10px">
      <div style="font-size:11px;font-weight:600;margin-bottom:4px;color:var(--text-muted)">RECOMMENDED HOOKS</div>
      <ol style="margin:0;padding-left:18px">${hooks.map(h => `<li style="font-size:12px;margin-bottom:4px">${esc(h)}</li>`).join("")}</ol>
    </div>
  ` : "";

  const aestheticsHtml = aesthetics.length ? `
    <div style="margin-top:10px">
      <div style="font-size:11px;font-weight:600;margin-bottom:4px;color:var(--text-muted)">VISUAL SIGNALS</div>
      <div>${aesthetics.map(a => `<span style="display:inline-block;background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:2px 10px;font-size:11px;margin:2px">${esc(a)}</span>`).join("")}</div>
    </div>
  ` : "";

  const validationHtml = validationLog.length ? `
    <details style="margin-top:10px">
      <summary style="font-size:11px;font-weight:600;color:var(--text-muted);cursor:pointer">VALIDATION LOG (${validationLog.length} checks)</summary>
      <div style="margin-top:6px">${validationLog.map(v => `
        <div style="font-size:11px;margin-bottom:4px;padding:4px 8px;background:var(--surface2);border-radius:4px">
          <span style="color:${v.verdict === 'removed' ? '#e05' : v.verdict === 'corrected' ? '#fa0' : '#0a6'};font-weight:600">${esc(v.verdict)}</span>
          — ${esc(v.claim)} <span style="color:var(--text-muted)">(${esc(v.source)})</span>
        </div>
      `).join("")}</div>
    </details>
  ` : "";

  return `
    <div class="card">
      <div class="card-title mb-8">${label}</div>
      ${data?.overall_summary ? `<div style="font-size:13px;margin-bottom:12px">${esc(data.overall_summary)}</div>` : ""}
      ${trendsHtml}
      ${hooksHtml}
      ${aestheticsHtml}
      ${validationHtml}
    </div>
  `;
}

function renderQuantitativeResult(label, data) {
  const charts = data?.charts || [];
  const findings = data?.key_quantitative_findings || [];
  const ranking = data?.engagement_ranking || [];
  const metrics = data?.metrics_summary || [];

  const chartsHtml = charts.map(c => `
    <div style="margin-bottom:12px">
      <div style="font-size:11px;font-weight:600;color:var(--text-muted);margin-bottom:4px">${esc(c.title || "Chart")}</div>
      ${c.description ? `<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">${esc(c.description)}</div>` : ""}
      <img src="data:image/png;base64,${c.image_base64}" alt="${esc(c.title || 'chart')}" style="max-width:100%;border-radius:6px;border:1px solid var(--border)" />
    </div>
  `).join("");

  const findingsHtml = findings.length ? `
    <div style="margin-top:10px">
      <div style="font-size:11px;font-weight:600;margin-bottom:4px;color:var(--text-muted)">KEY FINDINGS</div>
      <ol style="margin:0;padding-left:18px">${findings.map(f => `<li style="font-size:12px;margin-bottom:4px">${esc(f)}</li>`).join("")}</ol>
    </div>
  ` : "";

  const metricsHtml = metrics.length ? `
    <table style="width:100%;border-collapse:collapse;font-size:11px;margin-top:10px">
      <thead><tr style="border-bottom:1px solid var(--border)">
        <th style="text-align:left;padding:4px 8px;color:var(--text-muted)">Platform</th>
        <th style="text-align:left;padding:4px 8px;color:var(--text-muted)">Metric</th>
        <th style="text-align:right;padding:4px 8px;color:var(--text-muted)">Value</th>
      </tr></thead>
      <tbody>${metrics.map(m => `<tr style="border-bottom:1px solid var(--border)">
        <td style="padding:4px 8px">${esc(m.platform)}</td>
        <td style="padding:4px 8px;color:var(--text-muted)">${esc(m.metric)}</td>
        <td style="padding:4px 8px;text-align:right;font-weight:600">${typeof m.value === "number" ? m.value.toLocaleString() : esc(String(m.value))} <span style="color:var(--text-muted)">${esc(m.unit || "")}</span></td>
      </tr>`).join("")}</tbody>
    </table>
  ` : "";

  return `
    <div class="card">
      <div class="card-title mb-8">${label}</div>
      ${chartsHtml}
      ${findingsHtml}
      ${metricsHtml}
      ${data?.data_limitations ? `<div style="font-size:11px;color:var(--text-muted);margin-top:8px;font-style:italic">${esc(data.data_limitations)}</div>` : ""}
    </div>
  `;
}

function renderSentimentResult(label, data) {
  const sentiment = data?.overall_sentiment || "";
  const score = data?.sentiment_score;
  const breakdown = data?.platform_breakdown || [];
  const unmetNeeds = data?.unmet_needs || [];
  const drivers = data?.positive_drivers || [];
  const concerns = data?.concerns || [];

  const sentimentColor = { positive: "#0a6", neutral: "#888", mixed: "#fa0", negative: "#e05" };
  const badgeColor = sentimentColor[sentiment] || "#888";

  const breakdownHtml = breakdown
    .filter(b => b.status !== "unavailable")
    .map(b => `
      <details style="margin-bottom:8px">
        <summary style="cursor:pointer;font-size:12px;font-weight:600">${esc(b.platform)} <span style="color:${sentimentColor[b.sentiment] || '#888'};font-weight:normal">${esc(b.sentiment)}</span></summary>
        <div style="padding:6px 0 0 8px">
          ${(b.key_themes || []).map(t => `<span style="display:inline-block;background:var(--surface2);border-radius:4px;padding:1px 6px;font-size:10px;margin:2px">${esc(t)}</span>`).join("")}
          ${(b.representative_quotes || []).map(q => `
            <blockquote style="border-left:2px solid var(--border);margin:6px 0;padding-left:8px;font-size:11px;color:var(--text-muted)">
              "${esc(q.quote)}"
              ${q.url ? `<br><a href="${esc(q.url)}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:underline;font-size:10px">${esc(q.source_label || q.url)}</a>` : ""}
            </blockquote>
          `).join("")}
        </div>
      </details>
    `).join("");

  const listHtml = (items, color, title) => items.length ? `
    <div style="margin-top:8px">
      <div style="font-size:11px;font-weight:600;color:var(--text-muted);margin-bottom:4px">${title}</div>
      <ul style="margin:0;padding-left:18px">${items.map(i => `<li style="font-size:11px;margin-bottom:2px;color:${color}">${esc(i)}</li>`).join("")}</ul>
    </div>
  ` : "";

  return `
    <div class="card">
      <div class="card-title mb-8">${label}</div>
      <div style="margin-bottom:10px">
        <span style="background:${badgeColor};color:#fff;border-radius:4px;padding:2px 8px;font-size:12px;font-weight:600">${esc(sentiment)}</span>
        ${score != null ? `<span style="font-size:11px;color:var(--text-muted);margin-left:8px">score: ${score}</span>` : ""}
      </div>
      ${data?.overall_narrative ? `<div style="font-size:12px;margin-bottom:12px">${esc(data.overall_narrative)}</div>` : ""}
      ${breakdownHtml}
      ${listHtml(unmetNeeds, "#e05", "UNMET NEEDS")}
      ${listHtml(drivers, "#0a6", "POSITIVE DRIVERS")}
      ${listHtml(concerns, "#fa0", "CONCERNS")}
    </div>
  `;
}

function renderCompetitorResult(label, data) {
  const themes = data?.competitor_themes || [];
  const whitespace = data?.whitespace_opportunities || [];

  const themesHtml = themes.map(t => `
    <div style="border:1px solid var(--border);border-radius:6px;padding:10px;margin-bottom:8px">
      <div style="font-weight:600;font-size:13px;margin-bottom:2px">${esc(t.theme)}</div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:4px">${esc(t.description)}</div>
      ${(t.brands_using || []).map(b => `<span style="display:inline-block;background:var(--surface2);border-radius:4px;padding:1px 6px;font-size:10px;margin-right:4px">${esc(b)}</span>`).join("")}
      ${t.evidence ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;font-style:italic">${esc(t.evidence)}</div>` : ""}
      ${renderSources(t.sources)}
    </div>
  `).join("");

  const whitespaceHtml = whitespace.map(w => `
    <div style="border:1px solid var(--border);border-radius:6px;padding:10px;margin-bottom:8px;border-left:3px solid var(--accent)">
      <div style="font-weight:600;font-size:13px;margin-bottom:2px">${esc(w.angle)}</div>
      <div style="font-size:12px;margin-bottom:4px">${esc(w.rationale)}</div>
      ${w.risk ? `<div style="font-size:11px;color:#fa0">Risk: ${esc(w.risk)}</div>` : ""}
      ${renderSources(w.sources)}
    </div>
  `).join("");

  return `
    <div class="card">
      <div class="card-title mb-8">${label}</div>
      ${data?.positioning_map ? `<div style="font-size:12px;margin-bottom:12px">${esc(data.positioning_map)}</div>` : ""}
      ${themes.length ? `<div style="font-size:11px;font-weight:600;color:var(--text-muted);margin-bottom:6px">COMPETITOR THEMES</div>${themesHtml}` : ""}
      ${whitespace.length ? `<div style="font-size:11px;font-weight:600;color:var(--accent);margin-top:12px;margin-bottom:6px">WHITESPACE OPPORTUNITIES</div>${whitespaceHtml}` : ""}
      ${data?.recommended_differentiation ? `<div style="margin-top:10px;padding:10px;background:var(--surface2);border-radius:6px;font-size:12px"><strong>Recommended differentiation:</strong> ${esc(data.recommended_differentiation)}</div>` : ""}
    </div>
  `;
}

function renderGenericResult(label, data) {
  return `
    <div class="card">
      <div class="text-muted" style="font-size:11px;margin-bottom:4px">${label}</div>
      <pre style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:12px;font-size:11px;white-space:pre-wrap;word-break:break-word;color:var(--text-muted)">${JSON.stringify(data, null, 2)}</pre>
    </div>
  `;
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
