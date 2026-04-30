import { api, getToken } from "./api.js";
import { renderAgentTabs, setAgentError, setAgentRunning, updateAgentTab } from "./agent_tabs.js";

let _campaignId = null;
let _existingAdId = null;
let _selectedChannel = null;

export async function renderGenerate(campaignId, existingAdId = null) {
  _campaignId = campaignId;
  _existingAdId = existingAdId;
  _selectedChannel = null;

  let products = [], personas = [], existingAd = null, campaign = null;
  try {
    [products, personas, campaign] = await Promise.all([
      api.getProducts(campaignId),
      api.getPersonas(campaignId),
      api.get(`/campaigns/${campaignId}`),
    ]);
    if (existingAdId) {
      existingAd = await api.getAdvertisement(campaignId, existingAdId);
      _selectedChannel = existingAd?.target_channel || null;
    }
  } catch {}

  const pipelineState = existingAd?.pipeline_state || {};
  const evalData = existingAd?.evaluation_output;
  const brandScore = existingAd?.brand_consistency_score;

  return `
    <div class="page">
      <a href="#project/${campaignId}" style="color:var(--text-muted);font-size:12px;text-decoration:none">← Back to Project</a>
      <h1 class="page-title" style="margin-top:8px">Generate Advertisement</h1>

      <div style="display:flex;gap:24px;flex-wrap:wrap">
        <!-- Left: inputs + agent panel -->
        <div style="flex:1;min-width:300px">
          <form id="gen-form">
            <div class="card">
              <div class="card-title mb-8">Product & Inputs</div>
              <div class="form-group">
                <label>Product *</label>
                <select id="gen-product" required>
                  <option value="">Select a product…</option>
                  ${products.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join("")}
                </select>
              </div>
              <div class="form-group">
                <label>Target Audience</label>
                <input id="gen-audience" placeholder="Urban professionals aged 25-35" />
              </div>

              <!-- Expert-only inputs -->
              <div class="expert-only">
                <div class="form-group">
                  <label>Value Proposition</label>
                  <input id="gen-value-prop" placeholder="Lightest shoe for daily speed" />
                </div>
                <div class="form-group">
                  <label>Brand Positioning</label>
                  <input id="gen-positioning" placeholder="Premium performance, accessible price" />
                </div>
                <div class="form-group">
                  <label>Tone</label>
                  <input id="gen-tone" placeholder="Aspirational, clean, energetic" />
                </div>
                <div class="form-group">
                  <label>Extra Notes</label>
                  <textarea id="gen-notes" placeholder="Any other context for the agents…"></textarea>
                </div>
              </div>
            </div>

            <!-- Channel selector (expert) -->
            <div class="card expert-only">
              <div class="card-title mb-8">Target Channel</div>
              <div class="channel-selector" id="channel-selector">
                <button type="button" class="channel-btn" data-channel="">Any</button>
                <button type="button" class="channel-btn" data-channel="meta">Meta</button>
                <button type="button" class="channel-btn" data-channel="tiktok">TikTok</button>
                <button type="button" class="channel-btn" data-channel="youtube">YouTube</button>
              </div>
              <div class="text-muted" id="channel-hint" style="font-size:11px;margin-top:8px"></div>
            </div>

            ${personas.length ? `
              <div class="card">
                <div class="card-title mb-8">Personas (optional)</div>
                ${personas.map(p => `
                  <label class="checkbox-label mb-8">
                    <input type="checkbox" name="persona" value="${p.id}" />
                    <div>
                      <strong>${esc(p.name)}</strong>
                      <div class="text-muted" style="font-size:12px">${p.traits ? Object.values(p.traits).slice(0,2).join(" · ") : ""}</div>
                    </div>
                  </label>
                `).join("")}
              </div>
            ` : ""}

            <button type="submit" class="btn btn-primary" id="gen-btn" style="width:100%;justify-content:center">
              ✨ Generate Ad
            </button>
            <div class="error-msg" id="gen-error"></div>
          </form>

          <!-- Progress -->
          <div id="gen-progress-wrap" style="display:none;margin-top:16px">
            <div class="progress-bar-wrap">
              <div class="progress-bar-fill" id="gen-progress-bar" style="width:0%"></div>
            </div>
            <div id="gen-status-text" class="text-muted" style="font-size:12px;text-align:center"></div>
          </div>

          <!-- Cost summary (expert, shown after generation) -->
          <div id="cost-panel-wrap" class="expert-only" style="display:none"></div>
        </div>

        <!-- Right: agent tabs + result -->
        <div style="flex:1.2;min-width:300px">
          ${renderAgentTabs(pipelineState)}

          <!-- Evaluation score (shown if available) -->
          ${evalData ? renderEvalPanel(evalData, brandScore) : `<div id="eval-panel-slot"></div>`}

          <!-- Image result -->
          <div id="gen-result" style="display:${existingAd?.image_url ? 'block' : 'none'}">
            <hr />
            <div class="section-header">
              <div class="section-title">Generated Ads</div>
              <button class="btn btn-secondary btn-sm" id="ab-btn" ${existingAd?.image_url ? "" : "disabled"}>Generate A/B Variant</button>
            </div>
            <div class="ad-result">
              <div>
                <div class="ad-image-label">Primary Ad</div>
                <div class="ad-image-box">
                  ${existingAd?.image_url
                    ? `<img src="${existingAd.image_url}" alt="Generated ad">`
                    : `<span class="text-muted">Image will appear here</span>`}
                </div>
              </div>
              <div id="ab-variant-col" style="${existingAd?.ab_variant_url ? '' : 'display:none'}">
                <div class="ad-image-label">A/B Variant</div>
                <div class="ad-image-box">
                  ${existingAd?.ab_variant_url ? `<img src="${existingAd.ab_variant_url}" alt="Variant ad">` : ""}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderEvalPanel(evalData, brandScore) {
  const score = evalData?.overall_score ?? "—";
  const verdict = evalData?.verdict || "";
  return `
    <div class="eval-panel expert-only" id="eval-panel-slot">
      <div style="display:flex;align-items:center;gap:16px">
        <div>
          <div class="eval-score">${score}<span style="font-size:14px;color:var(--text-muted)">/10</span></div>
          <div class="eval-verdict">${esc(verdict)}</div>
        </div>
        ${brandScore != null ? `
          <div style="text-align:center">
            <div style="font-size:20px;font-weight:700;color:var(--success)">${Math.round(brandScore * 100)}%</div>
            <div class="eval-verdict">Brand Match</div>
          </div>
        ` : ""}
      </div>
      ${evalData?.improvements?.length ? `
        <div style="margin-top:10px">
          <div class="text-muted" style="font-size:11px;margin-bottom:4px">Improvements</div>
          ${evalData.improvements.map(i => `<div style="font-size:12px;padding:2px 0">• ${esc(i)}</div>`).join("")}
        </div>
      ` : ""}
    </div>
  `;
}

export function bindGenerate(campaignId) {
  _campaignId = campaignId;

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
    document.getElementById("cost-panel-wrap").style.display = "none";
    startSSE(payload);
  });

  document.getElementById("ab-btn")?.addEventListener("click", async () => {
    if (!_existingAdId) return;
    const btn = document.getElementById("ab-btn");
    btn.disabled = true;
    btn.textContent = "Generating…";
    try {
      const result = await api.post("/generate/ab-variant", { advertisement_id: _existingAdId });
      document.getElementById("ab-variant-col").style.display = "block";
      document.getElementById("ab-variant-col").querySelector(".ad-image-box").innerHTML =
        `<img src="${result.ab_variant_url}" alt="Variant ad">`;
    } catch (err) {
      document.getElementById("gen-error").textContent = "A/B variant failed: " + err.message;
    } finally {
      btn.textContent = "Generate A/B Variant";
      btn.disabled = false;
    }
  });
}

function updateChannelHint() {
  const hint = document.getElementById("channel-hint");
  if (!hint) return;
  const hints = {
    meta: "4:5 or 9:16 · ≤125 chars · static or short video",
    tiktok: "9:16 · sound-on · trend-native language · 15-60s",
    youtube: "16:9 · 6s bumper or 15-30s pre-roll",
    "": "No platform constraints applied",
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
        document.getElementById("gen-btn").disabled = false;
      });
    }
    readChunk();
  }).catch(err => {
    document.getElementById("gen-error").textContent = err.message;
    document.getElementById("gen-btn").disabled = false;
  });
}

function handleSSEEvent(evt) {
  const { event, agent, data, progress, total, advertisement_id } = evt;

  if (event === "agent_start") {
    setAgentRunning(agent);
    document.getElementById("gen-status-text").textContent = `Running: ${agent.replace(/_/g, " ")}…`;
  }

  if (event === "agent_complete") {
    updateAgentTab(agent, data);
    const pct = Math.round((progress / total) * 100);
    document.getElementById("gen-progress-bar").style.width = pct + "%";
    document.getElementById("gen-status-text").textContent = `Completed ${progress}/${total}: ${agent.replace(/_/g, " ")}`;
    if (advertisement_id) _existingAdId = advertisement_id;

    // Show evaluation/brand score panel when relevant agents complete
    if (agent === "evaluation_agent" || agent === "brand_consistency_agent") {
      refreshEvalPanel(advertisement_id);
    }
  }

  if (event === "error") {
    setAgentError(agent, data?.message || "Unknown error");
  }

  if (event === "image_ready") {
    document.getElementById("gen-result").style.display = "block";
    document.getElementById("ab-btn").disabled = false;
    const box = document.querySelector(".ad-image-box");
    if (box) box.innerHTML = `<img src="${data.url}" alt="Generated ad">`;
    if (data.url) {
      document.getElementById("gen-progress-bar").style.width = "100%";
      document.getElementById("gen-status-text").textContent = "Image generated!";
    }
  }

  if (event === "cost_summary") {
    renderCostPanel(data);
  }

  if (event === "done") {
    document.getElementById("gen-btn").disabled = false;
    document.getElementById("gen-status-text").textContent = "Generation complete!";
    if (advertisement_id) _existingAdId = advertisement_id;
  }
}

async function refreshEvalPanel(adId) {
  if (!adId || !_campaignId) return;
  try {
    const ad = await api.getAdvertisement(_campaignId, adId);
    const slot = document.getElementById("eval-panel-slot");
    if (slot && (ad.evaluation_output || ad.brand_consistency_score != null)) {
      slot.outerHTML = renderEvalPanel(ad.evaluation_output, ad.brand_consistency_score);
    }
  } catch {}
}

function renderCostPanel(data) {
  const wrap = document.getElementById("cost-panel-wrap");
  if (!wrap) return;
  const totalMs = Math.round(data.total_latency_ms || 0);
  const totalCost = (data.total_cost_usd || 0).toFixed(4);
  const perAgent = data.per_agent || [];
  wrap.style.display = "block";
  wrap.innerHTML = `
    <div class="cost-panel">
      <div class="cost-panel-title">Generation Summary</div>
      <div class="cost-row total">
        <span>Total Cost</span><span>$${totalCost}</span>
      </div>
      <div class="cost-row total">
        <span>Total Latency</span><span>${(totalMs / 1000).toFixed(1)}s</span>
      </div>
      ${perAgent.map(a => `
        <div class="cost-row">
          <span>${a.agent_name.replace(/_/g, " ")}</span>
          <span>${a.latency_ms != null ? Math.round(a.latency_ms) + "ms" : "—"}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
