import { api, getToken } from "./api.js";
import { renderAgentTabs, setAgentError, setAgentRunning, updateAgentTab } from "./agent_tabs.js";

let _campaignId = null;
let _existingAdId = null;

export async function renderGenerate(campaignId, existingAdId = null) {
  _campaignId = campaignId;
  _existingAdId = existingAdId;

  let products = [], personas = [], existingAd = null;
  try {
    [products, personas] = await Promise.all([
      api.getProducts(campaignId),
      api.getPersonas(campaignId),
    ]);
    if (existingAdId) {
      existingAd = await api.getAdvertisement(campaignId, existingAdId);
    }
  } catch {}

  const pipelineState = existingAd?.pipeline_state || {};

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
        </div>

        <!-- Right: agent tabs + result -->
        <div style="flex:1.2;min-width:300px">
          ${renderAgentTabs(pipelineState)}

          <!-- Image result (shown after generation) -->
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
                <div id="primary-ad-box"></div>
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

export function bindGenerate(campaignId) {
  _campaignId = campaignId;

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
      target_audience: document.getElementById("gen-audience").value.trim() || null,
      value_proposition: document.getElementById("gen-value-prop").value.trim() || null,
      positioning: document.getElementById("gen-positioning").value.trim() || null,
      tone: document.getElementById("gen-tone").value.trim() || null,
      extra_notes: document.getElementById("gen-notes").value.trim() || null,
    };

    document.getElementById("gen-progress-wrap").style.display = "block";
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
    }
  });
}

function startSSE(payload) {
  const url = "/generate?" + new URLSearchParams({ payload: JSON.stringify(payload) });
  const token = getToken();
  // Use fetch with POST + ReadableStream for SSE with auth header
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
            try {
              handleSSEEvent(JSON.parse(line.slice(6)));
            } catch {}
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

  if (event === "done") {
    document.getElementById("gen-btn").disabled = false;
    document.getElementById("gen-status-text").textContent = "Generation complete!";
    if (advertisement_id) _existingAdId = advertisement_id;
  }
}

function esc(s) { return (s || "").replace(/</g, "&lt;"); }
