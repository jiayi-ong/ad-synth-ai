const AGENTS = [
  { key: "product_profile",     label: "1 · Product Understanding",    icon: "📦" },
  { key: "audience_analysis",   label: "2 · Audience & Positioning",   icon: "🎯" },
  { key: "trend_research",      label: "3 · Trend Research",            icon: "📊" },
  { key: "competitor_analysis", label: "4 · Competitor Intel",          icon: "🔍" },
  { key: "creative_directions", label: "5 · Creative Strategy",         icon: "💡" },
  { key: "selected_persona",    label: "6 · Persona Selection",         icon: "👤" },
  { key: "image_gen_prompt",    label: "7 · Prompt Engineering",        icon: "✍️" },
  { key: "marketing_output",    label: "8 · Marketing Recommendations", icon: "📣" },
  { key: "evaluation_output",   label: "9 · Evaluation",                icon: "⭐" },
  { key: "channel_adaptation",  label: "10 · Channel Adaptation",       icon: "📱" },
  { key: "brand_consistency",   label: "11 · Brand Consistency",        icon: "🛡️" },
];

export function renderAgentTabs(pipelineState = {}) {
  return `
    <div class="agent-tabs" id="agent-tabs">
      ${AGENTS.map((a, i) => {
        const data = pipelineState[a.key];
        const hasData = data !== undefined && data !== null;
        const status = hasData ? "done" : "pending";
        return `
          <div class="agent-item">
            <div class="agent-header" onclick="toggleAgent('agent-body-${i}')">
              <div class="agent-status ${status}" id="agent-status-${i}"></div>
              <div class="agent-name">${a.icon} ${a.label}</div>
              <div class="agent-progress" id="agent-prog-${i}">${hasData ? "Done" : "Waiting"}</div>
            </div>
            <div class="agent-body ${hasData ? "open" : ""}" id="agent-body-${i}">
              <pre id="agent-pre-${i}">${hasData ? syntaxHighlight(data) : ""}</pre>
            </div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

export function updateAgentTab(agentKey, data) {
  const idx = AGENTS.findIndex(a => a.key === agentKey);
  if (idx === -1) return;
  const statusEl = document.getElementById(`agent-status-${idx}`);
  const progEl = document.getElementById(`agent-prog-${idx}`);
  const preEl = document.getElementById(`agent-pre-${idx}`);
  const bodyEl = document.getElementById(`agent-body-${idx}`);
  if (statusEl) { statusEl.className = "agent-status done"; }
  if (progEl) progEl.textContent = "Done";
  if (preEl) preEl.innerHTML = syntaxHighlight(data);
  if (bodyEl) bodyEl.classList.add("open");
}

export function setAgentRunning(agentKey) {
  const idx = AGENTS.findIndex(a => a.key === agentKey);
  if (idx === -1) return;
  const statusEl = document.getElementById(`agent-status-${idx}`);
  const progEl = document.getElementById(`agent-prog-${idx}`);
  if (statusEl) statusEl.className = "agent-status running";
  if (progEl) progEl.textContent = "Running…";
}

export function setAgentError(agentKey, message) {
  const idx = AGENTS.findIndex(a => a.key === agentKey);
  if (idx === -1) return;
  const statusEl = document.getElementById(`agent-status-${idx}`);
  const progEl = document.getElementById(`agent-prog-${idx}`);
  const preEl = document.getElementById(`agent-pre-${idx}`);
  if (statusEl) statusEl.className = "agent-status error";
  if (progEl) progEl.textContent = "Error";
  if (preEl) preEl.textContent = message;
}

window.toggleAgent = function(id) {
  document.getElementById(id)?.classList.toggle("open");
};

function syntaxHighlight(data) {
  const str = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  return str
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"([^"]+)":/g, `<span style="color:#7c9ef5">"$1"</span>:`)
    .replace(/: "([^"]*)"/g, `: <span style="color:#9cf07c">"$1"</span>`)
    .replace(/: (true|false|null)/g, `: <span style="color:#f0a03c">$1</span>`)
    .replace(/: (-?\d+\.?\d*)/g, `: <span style="color:#f07c7c">$1</span>`);
}
