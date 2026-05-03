import { renderStageData } from "./stage_renderers.js";
import { api } from "./api.js";

// ── Stage definitions ─────────────────────────────────────────────────────────
export const AGENTS = [
  { key: "product_profile",       short: "Product",     icon: "📦" },
  { key: "market_segmentation",   short: "Segments",    icon: "📊" },
  { key: "audience_analysis",     short: "Audience",    icon: "🎯" },
  { key: "trend_research",        short: "Trends",      icon: "📈" },
  { key: "competitor_analysis",   short: "Competitors", icon: "🔍" },
  { key: "pricing_analysis",      short: "Pricing",     icon: "💰" },
  { key: "creative_directions",   short: "Creative",    icon: "💡" },
  { key: "selected_persona",      short: "Persona",     icon: "👤" },
  { key: "image_gen_prompt",      short: "Prompts",     icon: "✍️" },
  { key: "campaign_architecture", short: "Campaign",    icon: "🗺️" },
  { key: "experiment_design",     short: "Experiments", icon: "🧪" },
  { key: "marketing_output",      short: "Marketing",   icon: "📣" },
  { key: "evaluation_output",     short: "Evaluation",  icon: "⭐" },
  { key: "channel_adaptation",    short: "Channel",     icon: "📱" },
  { key: "brand_consistency",     short: "Brand",       icon: "🛡️" },
  { key: "image_generation",      short: "Image Gen",   icon: "🖼️" },
];

// ── Stage state ────────────────────────────────────────────────────────────────
const _state = {};       // key → { status: "waiting"|"running"|"done"|"error", data: any }
const _timers = {};      // key → { startMs, elapsed, intervalId }
const _history = {};     // key → [v0_data, v1_data, ...]
const _histIdx = {};     // key → current version index (0-based)
let _openKey = null;
let _pipelineStartMs = null;
let _pipelineTotalInterval = null;
let _pipelineTotalElapsed = 0;
let _adId = null;
let _campaignId = null;
let _onRerunCallback = null;

AGENTS.forEach(a => { _state[a.key] = { status: "waiting", data: null }; });

// ── Render: list + detail panel layout ───────────────────────────────────────
export function renderAgentTabs(pipelineState = {}, opts = {}) {
  _adId = opts.adId || null;
  _campaignId = opts.campaignId || null;
  _onRerunCallback = opts.onRerun || null;

  AGENTS.forEach(a => {
    if (pipelineState[a.key] !== undefined && pipelineState[a.key] !== null) {
      _state[a.key] = { status: "done", data: pipelineState[a.key] };
    } else {
      _state[a.key] = { status: "waiting", data: null };
    }
  });

  if (opts.pipelineHistory) {
    Object.entries(opts.pipelineHistory).forEach(([k, versions]) => {
      _history[k] = versions;
      _histIdx[k] = versions.length;
    });
  }

  return `
    <div class="stage-list-layout" id="stage-list-layout">
      <!-- Left: stage list -->
      <div class="stage-list-col" id="stage-list-col">
        <div class="stage-list-header" id="stage-list-header">
          <span id="pipeline-progress" style="font-weight:700;color:var(--accent)">
            ${AGENTS.filter(a => _state[a.key].status === "done").length} / ${AGENTS.length}
          </span>
          <span style="color:var(--text-muted);font-size:12px"> stages complete</span>
          <span id="pipeline-total-time" style="font-size:12px;font-weight:600;color:var(--text);margin-left:8px"></span>
        </div>
        <div id="stage-list">
          ${AGENTS.map((a, i) => _rowHTML(a, i)).join("")}
        </div>
      </div>
      <!-- Right: detail panel -->
      <div class="stage-panel-col" id="stage-panel-col">
        <div id="stage-panel-wrap"></div>
      </div>
    </div>
  `;
}

function _rowHTML(agent, i) {
  const { status } = _state[agent.key];
  const elapsed = _timers[agent.key]?.elapsed || 0;
  const timeStr = (status === "running" || (status === "done" && elapsed > 0)) ? _fmtTime(elapsed) : "";
  const active = _openKey === agent.key ? " active" : "";
  return `
    <div class="stage-row${active} ${status}" id="stage-row-${i}" onclick="window._stageClick(${i})">
      <span class="stage-row-icon">${agent.icon}</span>
      <span class="stage-row-label">${agent.short}</span>
      <span class="stage-row-status">${_statusIcon(status)}</span>
      <span class="stage-row-time" id="stage-time-${i}">${timeStr}</span>
    </div>
  `;
}

function _statusIcon(status) {
  if (status === "done")    return `<span style="color:var(--accent)">✓</span>`;
  if (status === "running") return `<span class="stage-running-dot"></span>`;
  if (status === "error")   return `<span style="color:#c93d24">✕</span>`;
  return `<span style="color:var(--border)">○</span>`;
}

// ── Bind after render ─────────────────────────────────────────────────────────
export function bindWheelChart() {
  window._stageClick = function(i) {
    const key = AGENTS[i].key;
    if (_openKey === key) {
      _openKey = null;
      _renderPanel(null);
    } else {
      _openKey = key;
      _renderPanel(key);
    }
    _refreshAllRows();
  };

  _updateCenter();
}

// ── Panel rendering ───────────────────────────────────────────────────────────
function _renderPanel(key) {
  const wrap = document.getElementById("stage-panel-wrap");
  if (!wrap) return;
  if (!key) { wrap.innerHTML = ""; return; }

  const agentDef = AGENTS.find(a => a.key === key);
  const st = _state[key];
  const histVersions = _history[key] || [];
  const histIdx = _histIdx[key] ?? histVersions.length;
  const totalVersions = histVersions.length + (st.data !== null ? 1 : 0);
  const currentVersionLabel = totalVersions > 0 ? `v${histIdx + 1} / v${totalVersions}` : "";

  let displayData = st.data;
  if (histIdx < histVersions.length) {
    displayData = histVersions[histIdx];
  }

  const isImageStage = key === "image_generation";
  const supportsRerun = !isImageStage && (st.status === "done" || st.status === "error");
  const supportsRetryImage = isImageStage && (st.status === "error" || st.status === "done") && _adId;
  const downstreamNames = _getDownstreamNames(key);

  wrap.innerHTML = `
    <div class="stage-panel" id="stage-panel">
      <div class="stage-panel-header">
        <span class="stage-panel-title">${agentDef.icon} ${agentDef.short}</span>
        <div style="display:flex;align-items:center;gap:8px">
          ${totalVersions > 1 ? `
            <div class="stage-version-nav">
              <button onclick="window._stageHistPrev()" title="Previous version">‹</button>
              <span>${currentVersionLabel}</span>
              <button onclick="window._stageHistNext()" title="Next version">›</button>
            </div>
          ` : ""}
          <button onclick="window._stageClose()" style="background:none;border:none;cursor:pointer;font-size:16px;color:var(--text-muted)">✕</button>
        </div>
      </div>
      <div class="stage-panel-body">
        <div id="stage-data-display">
          ${displayData !== null ? renderStageData(key, displayData) : `<div class="text-muted" style="font-size:13px">No data yet — stage has not run.</div>`}
        </div>
        ${supportsRerun && _adId ? `
          <div class="stage-panel-actions">
            <button class="btn btn-primary btn-sm" onclick="window._stageRerun('${key}', false)">↺ Re-run</button>
            ${downstreamNames.length > 1 ? `<button class="btn btn-secondary btn-sm" onclick="window._stageRerun('${key}', true)">↺ Re-run + ${downstreamNames.length - 1} downstream</button>` : ""}
          </div>
          <div class="stage-extra-input">
            <label style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;display:block">Additional context for re-run (optional)</label>
            <textarea id="stage-extra-input" class="stage-extra-input-ta" placeholder="Add context to guide this stage's re-run…" rows="2"></textarea>
          </div>
        ` : ""}
        ${supportsRetryImage ? `
          <div class="stage-panel-actions">
            <button class="btn btn-primary btn-sm" id="retry-image-panel-btn" onclick="window._retryImageFromPanel()">↺ Retry Image Generation</button>
          </div>
        ` : ""}
        <div id="stage-rerun-error" class="error-msg" style="margin-top:6px"></div>
      </div>
    </div>
  `;

  window._stageClose = () => { _openKey = null; _renderPanel(null); _refreshAllRows(); };
  window._stageHistPrev = () => {
    const cur = _histIdx[key] ?? histVersions.length;
    if (cur > 0) { _histIdx[key] = cur - 1; _renderPanel(key); }
  };
  window._stageHistNext = () => {
    const cur = _histIdx[key] ?? histVersions.length;
    if (cur < histVersions.length) { _histIdx[key] = cur + 1; _renderPanel(key); }
  };
  window._stageRerun = async (stageKey, includeDownstream) => {
    const extraInput = document.getElementById("stage-extra-input")?.value.trim() || null;
    const errEl = document.getElementById("stage-rerun-error");
    const downstream = _getDownstreamNames(stageKey);
    if (downstream.length > 1) {
      const confirmed = await _showDepWarning(stageKey, downstream);
      if (!confirmed) return;
    }
    if (errEl) errEl.textContent = "";
    document.querySelectorAll(".stage-panel-actions .btn").forEach(b => b.disabled = true);
    try {
      await _startRerun(stageKey, extraInput, includeDownstream);
    } catch (err) {
      if (errEl) errEl.textContent = "Re-run failed: " + err.message;
      document.querySelectorAll(".stage-panel-actions .btn").forEach(b => b.disabled = false);
    }
  };

  window._retryImageFromPanel = async () => {
    if (!_adId) return;
    const btn = document.getElementById("retry-image-panel-btn");
    const errEl = document.getElementById("stage-rerun-error");
    if (btn) btn.disabled = true;
    if (errEl) errEl.textContent = "";
    try {
      setAgentRunning("image_generation");
      const { api } = await import("./api.js");
      const result = await api.retryImage(_adId);
      updateAgentTab("image_generation", { url: result.image_url });
      if (_onRerunCallback) _onRerunCallback();
    } catch (err) {
      setAgentError("image_generation", err.message);
      if (errEl) errEl.textContent = "Retry failed: " + err.message;
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  // Keep old global names as aliases for backward compatibility
  window._wheelClose = window._stageClose;
  window._wheelHistPrev = window._stageHistPrev;
  window._wheelHistNext = window._stageHistNext;
  window._wheelRerun = window._stageRerun;
}

function _getDownstreamNames(key) {
  const DOWNSTREAM = {
    product_profile:       ["product_profile","market_segmentation","audience_analysis","trend_research","competitor_analysis","pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    market_segmentation:   ["market_segmentation","audience_analysis","trend_research","competitor_analysis","pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    audience_analysis:     ["audience_analysis","trend_research","competitor_analysis","pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    trend_research:        ["trend_research","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    competitor_analysis:   ["competitor_analysis","pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    pricing_analysis:      ["pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    creative_directions:   ["creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    selected_persona:      ["selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    image_gen_prompt:      ["image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    campaign_architecture: ["campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    experiment_design:     ["experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    marketing_output:      ["marketing_output","brand_consistency"],
    evaluation_output:     ["evaluation_output","brand_consistency"],
    channel_adaptation:    ["channel_adaptation","brand_consistency"],
    brand_consistency:     ["brand_consistency"],
    image_generation:      ["image_generation"],
  };
  return (DOWNSTREAM[key] || [key]).map(k => AGENTS.find(a => a.key === k)?.short || k);
}

function _showDepWarning(key, downstreamNames) {
  return new Promise(resolve => {
    const overlay = document.createElement("div");
    overlay.className = "dep-modal-overlay";
    overlay.innerHTML = `
      <div class="dep-modal">
        <h3>⚠️ Re-run Dependencies</h3>
        <p style="font-size:13px;color:var(--text-muted)">Re-running <strong>${AGENTS.find(a=>a.key===key)?.short}</strong> will also invalidate these downstream stages:</p>
        <ul class="dep-modal-list">
          ${downstreamNames.slice(1).map(n => `<li>${n}</li>`).join("")}
        </ul>
        <div class="dep-modal-actions">
          <button class="btn btn-secondary btn-sm" id="dep-cancel">Cancel</button>
          <button class="btn btn-primary btn-sm" id="dep-confirm">Proceed</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    overlay.querySelector("#dep-cancel").onclick = () => { overlay.remove(); resolve(false); };
    overlay.querySelector("#dep-confirm").onclick = () => { overlay.remove(); resolve(true); };
  });
}

async function _startRerun(stageKey, extraInput, includeDownstream) {
  if (!_adId) return;
  const { getToken } = await import("./api.js");
  const token = getToken();

  const DOWNSTREAM_KEYS_MAP = {
    product_profile:       ["product_profile","market_segmentation","audience_analysis","trend_research","competitor_analysis","pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    market_segmentation:   ["market_segmentation","audience_analysis","trend_research","competitor_analysis","pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    audience_analysis:     ["audience_analysis","trend_research","competitor_analysis","pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    trend_research:        ["trend_research","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    competitor_analysis:   ["competitor_analysis","pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    pricing_analysis:      ["pricing_analysis","creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    creative_directions:   ["creative_directions","selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    selected_persona:      ["selected_persona","image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    image_gen_prompt:      ["image_gen_prompt","campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    campaign_architecture: ["campaign_architecture","experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    experiment_design:     ["experiment_design","marketing_output","evaluation_output","channel_adaptation","brand_consistency","image_generation"],
    marketing_output:      ["marketing_output","brand_consistency"],
    evaluation_output:     ["evaluation_output","brand_consistency"],
    channel_adaptation:    ["channel_adaptation","brand_consistency"],
    brand_consistency:     ["brand_consistency"],
    image_generation:      ["image_generation"],
  };
  for (const k of DOWNSTREAM_KEYS_MAP[stageKey] || [stageKey]) {
    _state[k] = { status: "waiting", data: null };
    _updateSegment(AGENTS.findIndex(a => a.key === k));
  }
  _updateCenter();

  const res = await fetch(`/generate/${_adId}/rerun-stage`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
    body: JSON.stringify({ stage_key: stageKey, extra_input: extraInput, rerun_downstream: includeDownstream }),
  });
  if (!res.ok) throw new Error(await res.text());

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  function readChunk() {
    reader.read().then(({ done, value }) => {
      if (done) { if (_onRerunCallback) _onRerunCallback(); return; }
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try { _handleRerunEvent(JSON.parse(line.slice(6))); } catch {}
        }
      }
      readChunk();
    });
  }
  readChunk();
}

function _handleRerunEvent(evt) {
  const { event, agent, data } = evt;
  if (event === "agent_start") setAgentRunning(agent);
  if (event === "agent_complete") {
    updateAgentTab(agent, data);
    if (_openKey === agent) _renderPanel(agent);
  }
  if (event === "error") setAgentError(agent || "pipeline", data?.message || "error");
  if (event === "done" || event === "cancelled") {
    document.querySelectorAll(".stage-panel-actions .btn").forEach(b => b.disabled = false);
  }
}

// ── Public API (called by generate.js SSE handler) ────────────────────────────
export function setAgentRunning(key) {
  const i = AGENTS.findIndex(a => a.key === key);
  if (i === -1) return;
  _state[key].status = "running";

  const startMs = Date.now();
  if (!_pipelineStartMs) {
    _pipelineStartMs = startMs;
    _startTotalTimer();
  }
  _timers[key] = { startMs, elapsed: 0 };
  _timers[key].intervalId = setInterval(() => {
    if (_timers[key]) {
      _timers[key].elapsed = Date.now() - startMs;
      const timeEl = document.getElementById(`stage-time-${i}`);
      if (timeEl) timeEl.textContent = _fmtTime(_timers[key].elapsed);
    }
  }, 200);

  _updateSegment(i);
  _updateCenter();
}

export function updateAgentTab(key, data) {
  const i = AGENTS.findIndex(a => a.key === key);
  if (i === -1) return;

  if (_state[key].data !== null) {
    if (!_history[key]) _history[key] = [];
    _history[key].push(_state[key].data);
    _histIdx[key] = _history[key].length;
  }

  _state[key] = { status: "done", data };

  if (_timers[key]?.intervalId) {
    clearInterval(_timers[key].intervalId);
    _timers[key].elapsed = _timers[key].elapsed || (Date.now() - _timers[key].startMs);
  }
  const finalElapsed = _timers[key]?.elapsed || 0;
  const timeEl = document.getElementById(`stage-time-${i}`);
  if (timeEl) timeEl.textContent = _fmtTime(finalElapsed);

  _updateSegment(i);
  _updateCenter();

  if (_openKey === key) _renderPanel(key);
}

export function setAgentError(key, message) {
  const i = AGENTS.findIndex(a => a.key === key);
  if (i === -1) return;
  _state[key] = { status: "error", data: { error: message } };
  if (_timers[key]?.intervalId) clearInterval(_timers[key].intervalId);
  _updateSegment(i);
}

export function resetWheel() {
  AGENTS.forEach((a, i) => {
    _state[a.key] = { status: "waiting", data: null };
    _updateSegment(i);
  });
  Object.values(_timers).forEach(t => { if (t?.intervalId) clearInterval(t.intervalId); });
  Object.keys(_timers).forEach(k => delete _timers[k]);
  _pipelineStartMs = null;
  _pipelineTotalElapsed = 0;
  if (_pipelineTotalInterval) { clearInterval(_pipelineTotalInterval); _pipelineTotalInterval = null; }
  _openKey = null;
  _renderPanel(null);
  _updateCenter();
}

export function stopTotalTimer() {
  if (_pipelineTotalInterval) { clearInterval(_pipelineTotalInterval); _pipelineTotalInterval = null; }
}

// ── Internal helpers ──────────────────────────────────────────────────────────
function _updateSegment(i) {
  const agent = AGENTS[i];
  const row = document.getElementById(`stage-row-${i}`);
  if (!row) return;
  const { status } = _state[agent.key];
  const active = _openKey === agent.key ? " active" : "";
  row.className = `stage-row${active} ${status}`;
  const statusEl = row.querySelector(".stage-row-status");
  if (statusEl) statusEl.innerHTML = _statusIcon(status);
}

function _refreshAllRows() {
  AGENTS.forEach((a, i) => _updateSegment(i));
}

function _updateCenter() {
  const doneCount = AGENTS.filter(a => _state[a.key].status === "done").length;
  const el = document.getElementById("pipeline-progress");
  if (el) el.textContent = `${doneCount} / ${AGENTS.length}`;
}

function _startTotalTimer() {
  _pipelineTotalInterval = setInterval(() => {
    if (_pipelineStartMs) {
      _pipelineTotalElapsed = Date.now() - _pipelineStartMs;
      const el = document.getElementById("pipeline-total-time");
      if (el) el.textContent = _fmtTime(_pipelineTotalElapsed);
    }
  }, 200);
}

function _fmtTime(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60).toString().padStart(2, "0");
  const s = (totalSec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}
