import { api, getToken } from "./api.js";
import {
  AGENTS,
  bindWheelChart,
  renderAgentTabs,
  resetWheel,
  setAgentError,
  setAgentRunning,
  stopTotalTimer,
  updateAgentTab,
} from "./agent_tabs.js";

let _campaignId = null;
let _existingAdId = null;
let _selectedChannel = null;
let _inputsCollapsed = false;   // true when viewing existing ad with collapsed inputs

export async function renderGenerate(campaignId, existingAdId = null) {
  _campaignId = campaignId;
  _existingAdId = existingAdId;
  _selectedChannel = null;
  _inputsCollapsed = !!existingAdId;

  let products = [], personas = [], existingAd = null, campaign = null;
  try {
    [products, personas, campaign] = await Promise.all([
      api.getAllProducts(),
      api.getAllPersonas(),
      api.get(`/campaigns/${campaignId}`),
    ]);
    if (existingAdId) {
      existingAd = await api.getAdvertisement(campaignId, existingAdId);
      _selectedChannel = existingAd?.target_channel || null;
    }
  } catch {}

  const pipelineState   = existingAd?.pipeline_state || {};
  const pipelineHistory = existingAd?.pipeline_state_history || {};

  // Pre-fill inputs when loading an existing ad
  const preProduct = existingAd?.product_id || "";
  const prePersonas = existingAd ? (existingAd.persona_ids || []) : [];

  const productName = products.find(p => p.id === preProduct)?.name || "Ad";

  return `
    <div class="page" style="padding:0;max-width:100%">

      <!-- SECTION 1 — Sticky inputs ─────────────────────────── -->
      <div class="gen-sticky-inputs" id="gen-sticky-inputs">

        ${existingAd ? `
          <!-- Collapsed summary bar when viewing existing ad -->
          <div class="gen-inputs-collapsed" id="gen-inputs-collapsed" onclick="window._genToggleInputs()">
            <span style="font-size:16px">📋</span>
            <div class="gen-inputs-collapsed-summary">
              <strong>${esc(productName)}</strong> · ${esc(new Date(existingAd.created_at).toLocaleDateString())}
              ${existingAd.target_channel ? `· <span class="tag" style="font-size:11px">${esc(existingAd.target_channel)}</span>` : ""}
            </div>
            <span style="font-size:12px;color:var(--accent)" id="gen-toggle-label">▼ Show inputs</span>
          </div>
        ` : ""}

        <div id="gen-inputs-body" style="${existingAd && _inputsCollapsed ? "display:none" : ""}">
          <div style="max-width:1100px;margin:0 auto;padding:0 0 12px">

            <form id="gen-form">
            <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start">

              <!-- Product + main inputs -->
              <div style="flex:2;min-width:280px">
                  <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
                    <div class="form-group" style="flex:1;min-width:200px;margin-bottom:0">
                      <label>Product *</label>
                      <select id="gen-product" required>
                        <option value="">Select a product…</option>
                        ${products.map(p => `<option value="${p.id}" ${p.id === preProduct ? "selected" : ""}>
                          ${esc(p.name)}${p.campaign_id !== campaignId ? " (other campaign)" : ""}
                        </option>`).join("")}
                      </select>
                    </div>
                    <div class="form-group" style="flex:1;min-width:180px;margin-bottom:0">
                      <label>Target Audience</label>
                      <input id="gen-audience" placeholder="Urban professionals 25-35" />
                    </div>
                    <div class="expert-only form-group" style="flex:1;min-width:160px;margin-bottom:0">
                      <label>Value Proposition</label>
                      <input id="gen-value-prop" />
                    </div>
                  </div>
                  <div class="expert-only" style="display:flex;gap:12px;flex-wrap:wrap;margin-top:8px">
                    <div class="form-group" style="flex:1;min-width:160px;margin-bottom:0">
                      <label>Brand Positioning</label>
                      <input id="gen-positioning" />
                    </div>
                    <div class="form-group" style="flex:1;min-width:160px;margin-bottom:0">
                      <label>Tone</label>
                      <input id="gen-tone" />
                    </div>
                    <div class="form-group" style="flex:1;min-width:200px;margin-bottom:0">
                      <label>Extra Notes</label>
                      <input id="gen-notes" />
                    </div>
                  </div>
                  <!-- Channel selector (expert) -->
                  <div class="expert-only" style="margin-top:8px">
                    <label style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;display:block">Target Channel</label>
                    <div class="channel-selector" id="channel-selector">
                      <button type="button" class="channel-btn" data-channel="">Any</button>
                      <button type="button" class="channel-btn" data-channel="meta">Meta</button>
                      <button type="button" class="channel-btn" data-channel="tiktok">TikTok</button>
                      <button type="button" class="channel-btn" data-channel="youtube">YouTube</button>
                    </div>
                    <div class="text-muted" id="channel-hint" style="font-size:11px;margin-top:4px"></div>
                  </div>
              </div>

              <!-- Persona selection (right of product) -->
              ${personas.length ? `
                <div style="flex:1;min-width:200px;max-width:280px">
                  <label style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;display:block">Personas (optional)</label>
                  <div style="max-height:140px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;padding:8px">
                    ${personas.map(p => `
                      <label class="checkbox-label mb-8">
                        <input type="checkbox" name="persona" value="${p.id}" ${prePersonas.includes(p.id) ? "checked" : ""} />
                        <div>
                          <strong style="font-size:13px">${esc(p.name)}</strong>
                          ${p.campaign_id !== campaignId ? ' <span class="text-muted" style="font-size:10px">(other)</span>' : ""}
                          <div class="text-muted" style="font-size:11px">${p.traits ? Object.values(p.traits).slice(0,2).join(" · ") : ""}</div>
                        </div>
                      </label>
                    `).join("")}
                  </div>
                </div>
              ` : ""}

              <!-- Action buttons -->
              <div style="display:flex;flex-direction:column;gap:8px;padding-top:20px;min-width:120px">
                <button type="submit" class="btn btn-primary" id="gen-btn" style="justify-content:center">
                  ✨ Generate
                </button>
                <button type="button" class="btn btn-interrupt btn-sm" id="gen-interrupt-btn" style="display:none;justify-content:center">
                  ⏹ Interrupt
                </button>
                <a href="#project/${campaignId}" style="font-size:11px;color:var(--text-muted);text-align:center;text-decoration:none">← Back</a>
              </div>

            </div><!-- end flex row -->
            </form>

            <div class="error-msg" id="gen-error" style="margin-top:4px"></div>

            <!-- Progress bar + status -->
            <div id="gen-progress-wrap" style="display:none;margin-top:8px">
              <div class="progress-bar-wrap">
                <div class="progress-bar-fill" id="gen-progress-bar" style="width:0%"></div>
              </div>
              <div id="gen-status-text" class="text-muted" style="font-size:11px;text-align:center;margin-top:2px"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Main content (scrollable) -->
      <div style="max-width:1100px;margin:0 auto;padding:16px 24px 48px">

        <!-- SECTION 2 — Pipeline stages -->
        <div class="gen-section">
          <div class="gen-section-title">🔄 Pipeline Stages</div>
          ${renderAgentTabs(pipelineState, {
            adId: existingAdId,
            campaignId,
            pipelineHistory,
          })}
        </div>

        <!-- SECTION 3 — Generated Images -->
        <div class="gen-section" id="gen-images-section" style="display:${(existingAd?.image_url || existingAd?.image_gen_prompt) ? "block" : "none"}">
          <div class="gen-section-title">🖼️ Generated Ads</div>
          <div class="gen-images-row" id="gen-images-row">
            ${_renderImages(existingAd, existingAdId)}
          </div>
        </div>

        <!-- SECTION 4 — Strategic Summary -->
        <div class="gen-section" id="gen-summary-section" style="display:${existingAd?.marketing_output ? "block" : "none"}">
          <div class="gen-section-title">📋 Strategic Summary</div>
          <div id="gen-summary-content">
            ${existingAd ? renderStrategicSummary(existingAd.marketing_output, existingAd.evaluation_output) : ""}
          </div>
        </div>

        <!-- SECTION 5 — Latency & Cost -->
        <div class="gen-section expert-only" id="gen-cost-section" style="display:${existingAd?.pipeline_state?._telemetry ? "block" : "none"}">
          <div class="gen-section-title">💰 Latency & Cost</div>
          <div id="gen-cost-content">
            ${existingAd?.pipeline_state?._telemetry ? renderCostTable(existingAd.pipeline_state._telemetry) : ""}
          </div>
        </div>

      </div>
    </div>
  `;
}

function _renderImages(existingAd, adId) {
  const primaryUrl = existingAd?.image_url;
  const abUrl      = existingAd?.ab_variant_url;
  const primaryPrompt = existingAd?.image_gen_prompt || "";
  const abPrompt      = existingAd?.ab_variant_prompt || "";

  return `
    <!-- Primary Ad -->
    <div class="gen-image-col">
      <div class="gen-image-col-label">Primary Ad</div>
      <div class="ad-image-box" id="primary-image-box">
        ${primaryUrl
          ? `<img src="${esc(primaryUrl)}" alt="Generated ad">`
          : `<span class="text-muted" style="font-size:12px">Image will appear here</span>`}
      </div>
      ${!primaryUrl && primaryPrompt && adId ? `
        <div style="margin-top:8px">
          <button class="btn btn-secondary btn-sm" id="retry-primary-image-btn">↺ Retry Image Generation</button>
          <div class="error-msg" id="retry-image-error" style="margin-top:4px"></div>
        </div>
      ` : ""}
      ${primaryPrompt ? `
        <div class="gen-prompt-toggle" onclick="window._genTogglePrompt('primary-prompt')">▶ Show image prompt</div>
        <div class="gen-prompt-text" id="primary-prompt">${esc(primaryPrompt)}</div>
      ` : `<div id="primary-prompt-slot"></div>`}
    </div>

    <!-- A/B Variant -->
    <div class="gen-image-col" id="ab-variant-col" style="${abUrl ? "" : "display:none"}">
      <div class="gen-image-col-label">A/B Variant</div>
      <div class="ad-image-box" id="ab-image-box">
        ${abUrl ? `<img src="${esc(abUrl)}" alt="Variant ad">` : ""}
      </div>
      ${abPrompt ? `
        <div class="gen-prompt-toggle" onclick="window._genTogglePrompt('ab-prompt')">▶ Show image prompt</div>
        <div class="gen-prompt-text" id="ab-prompt">${esc(abPrompt)}</div>
      ` : `<div id="ab-prompt-slot"></div>`}
      <!-- Custom A/B regeneration -->
      <div style="margin-top:10px">
        <div class="form-group" style="margin-bottom:6px">
          <label>Custom edit (optional)</label>
          <textarea id="ab-custom-prompt" placeholder="Describe changes to make while keeping all else the same…" rows="2"></textarea>
        </div>
        <button class="btn btn-secondary btn-sm" id="ab-btn" ${!adId ? "disabled" : ""}>↺ Regenerate A/B</button>
        <div class="error-msg" id="ab-error" style="margin-top:4px"></div>
      </div>
    </div>

    <!-- Show A/B button when no variant yet -->
    <div id="ab-gen-col" style="${abUrl ? "display:none" : ""}">
      <div class="gen-image-col-label">A/B Variant</div>
      <div style="padding:16px 0">
        <button class="btn btn-secondary btn-sm" id="ab-btn-gen" ${!adId ? "disabled" : ""}>+ Generate A/B Variant</button>
      </div>
    </div>
  `;
}

function renderStrategicSummary(marketingOutput, evalOutput) {
  const mo = typeof marketingOutput === "string" ? _tryParse(marketingOutput) : marketingOutput;
  const ev = typeof evalOutput === "string" ? _tryParse(evalOutput) : evalOutput;
  if (!mo && !ev) return "";

  const slogan = mo?.product_slogan || "";
  const verdict = ev?.verdict || "";
  const recs = [...(mo?.improvement_recommendations || []), ...(ev?.improvements || ev?.improvement_suggestions || [])];
  const platforms = mo?.recommended_platforms || [];
  const brandAlignment = mo?.brand_alignment || "";

  return `
    <div class="gen-summary">
      ${slogan ? `<div class="gen-slogan">"${esc(slogan)}"</div>` : ""}
      ${verdict ? `<div style="margin-bottom:12px"><span class="verdict-badge">${esc(verdict)}</span></div>` : ""}
      ${platforms.length ? `
        <div class="gen-takeaway">
          <div class="gen-takeaway-icon">📱</div>
          <div class="gen-takeaway-text"><strong>Top Channels:</strong> ${platforms.slice(0,3).map(p => esc(p.platform || p)).join(", ")}</div>
        </div>
      ` : ""}
      ${brandAlignment ? `
        <div class="gen-takeaway">
          <div class="gen-takeaway-icon">🛡️</div>
          <div class="gen-takeaway-text"><strong>Brand Alignment:</strong> ${esc(brandAlignment)}</div>
        </div>
      ` : ""}
      ${recs.slice(0, 3).map(r => {
        const text = typeof r === "string" ? r : (r.recommendation || r.suggestion || r.text || "");
        return text ? `
          <div class="gen-takeaway">
            <div class="gen-takeaway-icon">💡</div>
            <div class="gen-takeaway-text">${esc(text)}</div>
          </div>
        ` : "";
      }).join("")}
    </div>
  `;
}

function renderCostTable(telemetry) {
  if (!telemetry) return "";
  const agents = telemetry.agents || [];
  const totalCost = telemetry.total_cost_usd || 0;
  const totalMs = telemetry.total_latency_ms || 0;
  return `
    <table class="cost-table">
      <thead>
        <tr>
          <th>Agent</th>
          <th>Latency</th>
          <th>In Tokens</th>
          <th>Out Tokens</th>
          <th>Cost (USD)</th>
        </tr>
      </thead>
      <tbody id="cost-table-body">
        ${agents.map(a => `
          <tr>
            <td>${esc((a.agent || "").replace(/_/g, " "))}</td>
            <td>${_fmtMs(a.latency_ms)}</td>
            <td>${_fmtNum(a.input_tokens)}</td>
            <td>${_fmtNum(a.output_tokens)}</td>
            <td>$${(a.cost_usd || 0).toFixed(4)}</td>
          </tr>
        `).join("")}
      </tbody>
      <tfoot>
        <tr class="total-row">
          <td>TOTAL</td>
          <td>${_fmtMs(totalMs)}</td>
          <td>—</td>
          <td>—</td>
          <td>$${totalCost.toFixed(4)}</td>
        </tr>
      </tfoot>
    </table>
  `;
}

// ── Bind ───────────────────────────────────────────────────────────────────────
export function bindGenerate(campaignId) {
  _campaignId = campaignId;

  // Wheel
  bindWheelChart();

  // Collapsed inputs toggle
  window._genToggleInputs = () => {
    const body = document.getElementById("gen-inputs-body");
    const label = document.getElementById("gen-toggle-label");
    if (!body) return;
    _inputsCollapsed = body.style.display !== "none";
    body.style.display = _inputsCollapsed ? "none" : "";
    if (label) label.textContent = _inputsCollapsed ? "▼ Show inputs" : "▲ Hide inputs";
  };

  // Prompt text toggle
  window._genTogglePrompt = (id) => {
    const el = document.getElementById(id);
    const toggle = el?.previousElementSibling;
    if (!el) return;
    el.classList.toggle("open");
    if (toggle) toggle.textContent = el.classList.contains("open") ? "▲ Hide image prompt" : "▶ Show image prompt";
  };

  // Channel selector
  document.querySelectorAll(".channel-btn").forEach(btn => {
    if (btn.dataset.channel === (_selectedChannel || "")) btn.classList.add("active");
    btn.addEventListener("click", () => {
      document.querySelectorAll(".channel-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      _selectedChannel = btn.dataset.channel || null;
      updateChannelHint();
    });
  });
  updateChannelHint();

  // Generate form submit
  document.getElementById("gen-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("gen-btn");
    btn.disabled = true;
    document.getElementById("gen-error").textContent = "";

    const productId = document.getElementById("gen-product").value;
    if (!productId) {
      document.getElementById("gen-error").textContent = "Please select a product.";
      btn.disabled = false;
      return;
    }

    const personaIds = [...document.querySelectorAll('input[name="persona"]:checked')].map(cb => cb.value);
    const payload = {
      campaign_id: campaignId,
      product_id: productId,
      persona_ids: personaIds,
      target_audience: document.getElementById("gen-audience")?.value.trim() || null,
      value_proposition: document.getElementById("gen-value-prop")?.value.trim() || null,
      positioning: document.getElementById("gen-positioning")?.value.trim() || null,
      tone: document.getElementById("gen-tone")?.value.trim() || null,
      extra_notes: document.getElementById("gen-notes")?.value.trim() || null,
      target_channel: _selectedChannel || null,
    };

    document.getElementById("gen-progress-wrap").style.display = "block";
    document.getElementById("gen-interrupt-btn").style.display = "";

    // Reset wheel and result sections
    resetWheel();
    document.getElementById("gen-images-section").style.display = "none";
    document.getElementById("gen-summary-section").style.display = "none";
    document.getElementById("gen-cost-section").style.display = "none";

    startSSE(payload);
  });

  // Interrupt button
  document.getElementById("gen-interrupt-btn")?.addEventListener("click", async () => {
    if (!_existingAdId) return;
    const btn = document.getElementById("gen-interrupt-btn");
    btn.disabled = true;
    btn.textContent = "Interrupting…";
    try {
      await api.post(`/generate/${_existingAdId}/cancel`, {});
    } catch {}
  });

  // A/B variant buttons
  document.getElementById("ab-btn")?.addEventListener("click", handleAbRegen);
  document.getElementById("ab-btn-gen")?.addEventListener("click", handleAbRegen);

  // Retry primary image button (shown when image generation failed)
  document.getElementById("retry-primary-image-btn")?.addEventListener("click", async () => {
    if (!_existingAdId) return;
    const btn = document.getElementById("retry-primary-image-btn");
    const errEl = document.getElementById("retry-image-error");
    if (btn) { btn.disabled = true; btn.textContent = "⏳ Retrying…"; }
    if (errEl) errEl.textContent = "";
    try {
      setAgentRunning("image_generation");
      const result = await api.retryImage(_existingAdId);
      const primaryBox = document.getElementById("primary-image-box");
      if (primaryBox) primaryBox.innerHTML = `<img src="${esc(result.image_url)}" alt="Generated ad">`;
      updateAgentTab("image_generation", { url: result.image_url });
      if (btn) btn.style.display = "none";
    } catch (err) {
      setAgentError("image_generation", err.message);
      if (errEl) errEl.textContent = "Retry failed: " + err.message;
      if (btn) { btn.disabled = false; btn.textContent = "↺ Retry Image Generation"; }
    }
  });
}

async function handleAbRegen() {
  if (!_existingAdId) return;
  const btn = document.getElementById("ab-btn") || document.getElementById("ab-btn-gen");
  const errEl = document.getElementById("ab-error");
  const originalLabel = btn?.textContent || "↺ Regenerate A/B";
  if (btn) { btn.disabled = true; btn.textContent = "⏳ Regenerating…"; }
  if (errEl) errEl.textContent = "";
  const customPrompt = document.getElementById("ab-custom-prompt")?.value.trim() || null;

  try {
    const result = await api.post("/generate/ab-variant", {
      advertisement_id: _existingAdId,
      custom_prompt: customPrompt || null,
    });
    // Show A/B column
    const abCol = document.getElementById("ab-variant-col");
    const genCol = document.getElementById("ab-gen-col");
    if (abCol) abCol.style.display = "";
    if (genCol) genCol.style.display = "none";
    const abBox = document.getElementById("ab-image-box");
    if (abBox) abBox.innerHTML = `<img src="${esc(result.ab_variant_url)}" alt="Variant ad">`;
  } catch (err) {
    if (errEl) errEl.textContent = "A/B failed: " + err.message;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = originalLabel; }
  }
}

function updateChannelHint() {
  const hint = document.getElementById("channel-hint");
  if (!hint) return;
  const hints = {
    meta: "4:5 or 9:16 · ≤125 chars · static or short video",
    tiktok: "9:16 · sound-on · trend-native language · 15-60s",
    youtube: "16:9 · 6s bumper or 15-30s pre-roll",
    "": "",
  };
  hint.textContent = hints[_selectedChannel || ""] || "";
}

function startSSE(payload) {
  const token = getToken();
  fetch("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
    body: JSON.stringify(payload),
  }).then(res => {
    if (!res.ok) throw new Error("Generation request failed");
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    function readChunk() {
      reader.read().then(({ done, value }) => {
        if (done) return;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try { handleSSEEvent(JSON.parse(line.slice(6))); } catch {}
          }
        }
        readChunk();
      }).catch(err => {
        document.getElementById("gen-error").textContent = "Stream error: " + err.message;
        _resetButtons();
      });
    }
    readChunk();
  }).catch(err => {
    document.getElementById("gen-error").textContent = err.message;
    _resetButtons();
  });
}

function handleSSEEvent(evt) {
  const { event, agent, data, progress, total, advertisement_id } = evt;

  if (event === "started") {
    if (advertisement_id) _existingAdId = advertisement_id;
  }

  if (event === "agent_start") {
    setAgentRunning(agent);
    setStatus(`Running: ${_agentLabel(agent)}…`);
  }

  if (event === "agent_complete") {
    updateAgentTab(agent, data);
    const pct = Math.round((progress / total) * 100);
    document.getElementById("gen-progress-bar").style.width = pct + "%";
    setStatus(`${progress}/${total} · ${_agentLabel(agent)}`);
    if (advertisement_id) _existingAdId = advertisement_id;

    // Show summary section when marketing agent completes
    if (agent === "marketing_output" || agent === "evaluation_output") {
      _tryUpdateSummary(advertisement_id);
    }
  }

  if (event === "image_generating") {
    setAgentRunning("image_generation");
    setStatus("Generating image…");
    document.getElementById("gen-progress-bar").style.width = "95%";
  }

  if (event === "image_ready") {
    updateAgentTab("image_generation", { url: data?.url, variant_url: data?.variant_url });
    document.getElementById("gen-images-section").style.display = "block";
    document.getElementById("gen-progress-bar").style.width = "100%";
    setStatus("Image generated!");

    const primaryBox = document.getElementById("primary-image-box");
    if (primaryBox && data?.url) {
      primaryBox.innerHTML = `<img src="${esc(data.url)}" alt="Generated ad">`;
    }
    if (data?.variant_url) {
      const abCol = document.getElementById("ab-variant-col");
      const genCol = document.getElementById("ab-gen-col");
      if (abCol) abCol.style.display = "";
      if (genCol) genCol.style.display = "none";
      const abBox = document.getElementById("ab-image-box");
      if (abBox) abBox.innerHTML = `<img src="${esc(data.variant_url)}" alt="Variant ad">`;
    }
    if (_existingAdId) {
      _loadAndShowPrompts(_existingAdId);
    }
    // Enable A/B buttons
    const abBtn = document.getElementById("ab-btn") || document.getElementById("ab-btn-gen");
    if (abBtn) abBtn.disabled = false;
  }

  if (event === "cost_summary") {
    _renderCostSection(data);
  }

  if (event === "error") {
    const msg = data?.message || "Unknown error";
    if (!agent || agent === "pipeline") {
      document.getElementById("gen-error").textContent = `Error: ${msg}`;
    } else {
      setAgentError(agent, msg);
      if (agent === "image_generation") {
        document.getElementById("gen-error").textContent = `Image failed: ${msg}`;
      }
    }
  }

  if (event === "done") {
    _resetButtons();
    stopTotalTimer();
    const status = evt.status;
    setStatus(status === "completed" ? "Generation complete!" : `Finished (${status})`);
    if (advertisement_id) _existingAdId = advertisement_id;
  }

  if (event === "cancelled") {
    _resetButtons();
    stopTotalTimer();
    setStatus("Generation interrupted — results saved so far.");
    const intBtn = document.getElementById("gen-interrupt-btn");
    if (intBtn) { intBtn.style.display = "none"; intBtn.disabled = false; intBtn.textContent = "⏹ Interrupt"; }
  }
}

async function _tryUpdateSummary(adId) {
  if (!adId || !_campaignId) return;
  try {
    const ad = await api.getAdvertisement(_campaignId, adId);
    if (ad.marketing_output || ad.evaluation_output) {
      const summarySection = document.getElementById("gen-summary-section");
      const summaryContent = document.getElementById("gen-summary-content");
      if (summaryContent) summaryContent.innerHTML = renderStrategicSummary(ad.marketing_output, ad.evaluation_output);
      if (summarySection) summarySection.style.display = "block";
    }
  } catch {}
}

async function _loadAndShowPrompts(adId) {
  if (!adId || !_campaignId) return;
  try {
    const ad = await api.getAdvertisement(_campaignId, adId);
    if (ad.image_gen_prompt) {
      _upsertPromptDisplay("primary-prompt-slot", "primary-prompt", ad.image_gen_prompt);
    }
    if (ad.ab_variant_prompt) {
      _upsertPromptDisplay("ab-prompt-slot", "ab-prompt", ad.ab_variant_prompt);
    }
  } catch {}
}

function _upsertPromptDisplay(slotId, promptId, promptText) {
  const slot = document.getElementById(slotId);
  if (slot) {
    slot.outerHTML = `
      <div class="gen-prompt-toggle" onclick="window._genTogglePrompt('${promptId}')">▶ Show image prompt</div>
      <div class="gen-prompt-text" id="${promptId}">${esc(promptText)}</div>
    `;
  }
}

function _renderCostSection(data) {
  const section = document.getElementById("gen-cost-section");
  const content = document.getElementById("gen-cost-content");
  if (!section || !content) return;
  const agents = data.per_agent || [];
  const totalCost = data.total_cost_usd || 0;
  const totalMs = data.total_latency_ms || 0;

  // Append new rows to existing table or create fresh
  const existing = document.getElementById("cost-table-body");
  if (existing) {
    agents.forEach(a => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${esc((a.agent || "").replace(/_/g, " "))}</td>
        <td>${_fmtMs(a.latency_ms)}</td>
        <td>${_fmtNum(a.input_tokens)}</td>
        <td>${_fmtNum(a.output_tokens)}</td>
        <td>$${(a.cost_usd || 0).toFixed(4)}</td>
      `;
      existing.appendChild(tr);
    });
  } else {
    content.innerHTML = renderCostTable({ agents, total_cost_usd: totalCost, total_latency_ms: totalMs });
  }
  section.style.display = "block";
}

function _resetButtons() {
  const btn = document.getElementById("gen-btn");
  if (btn) btn.disabled = false;
  const intBtn = document.getElementById("gen-interrupt-btn");
  if (intBtn) intBtn.style.display = "none";
}

function setStatus(text) {
  const el = document.getElementById("gen-status-text");
  if (el) el.textContent = text;
}

function _agentLabel(key) {
  return AGENTS.find(a => a.key === key)?.short || key.replace(/_/g, " ");
}

function _fmtMs(ms) {
  if (!ms) return "—";
  const s = ms / 1000;
  if (s < 60) return s.toFixed(1) + "s";
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}

function _fmtNum(n) {
  if (!n) return "—";
  return n.toLocaleString();
}

function _tryParse(v) {
  if (!v) return null;
  if (typeof v === "object") return v;
  try { return JSON.parse(v); } catch { return null; }
}

function esc(s) { return (s || "").toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
