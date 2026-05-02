import { api } from "./api.js";

let _campaignId = null;
let _allAds = [];
let _allProducts = [];
let _adSortDir = "desc";

export async function renderProject(campaignId) {
  _campaignId = campaignId;
  _adSortDir = "desc";
  let campaign, products, personas, ads;
  try {
    [campaign, products, personas, ads] = await Promise.all([
      api.get(`/campaigns/${campaignId}`),
      api.getProducts(campaignId),
      api.getPersonas(campaignId),
      api.getAdvertisements(campaignId),
    ]);
  } catch (e) {
    return `<div class="page"><p class="text-muted">Failed to load project: ${e.message}</p></div>`;
  }
  _allProducts = products;
  _allAds = ads;

  return `
    <div class="page">
      <div class="section-header" style="margin-bottom:4px">
        <div>
          <a href="#campaigns" style="color:var(--text-muted);font-size:12px;text-decoration:none">← Campaigns</a>
          <h1 class="page-title" style="margin-top:4px;margin-bottom:0">${esc(campaign.name)}</h1>
          ${campaign.mission ? `<div class="text-muted" style="font-size:13px">${esc(campaign.mission)}</div>` : ""}
        </div>
        <button class="btn btn-primary" id="go-generate-btn">Generate Ad</button>
      </div>

      <div class="tabs mt-16" id="project-tabs">
        <div class="tab active" data-tab="products">Products</div>
        <div class="tab" data-tab="personas">Personas</div>
        <div class="tab" data-tab="ads">Advertisements</div>
        <div class="tab expert-only" data-tab="config">Campaign Config</div>
      </div>

      <div id="tab-products">${renderProductsTab(products)}</div>
      <div id="tab-personas" style="display:none">${renderPersonasTab(personas)}</div>
      <div id="tab-ads" style="display:none">${renderAdsTab(ads, products)}</div>
      <div id="tab-config" style="display:none">${renderConfigTab(campaign)}</div>
    </div>
  `;
}

function renderProductsTab(products) {
  const cards = products.map(p => `
    <div class="card" style="cursor:default" id="product-card-${p.id}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div style="flex:1">
          <div class="card-title">${esc(p.name)}</div>
          <div class="card-meta">${esc(p.description || "No description")}</div>
          ${p.image_path ? `<div class="card-meta mt-16">📎 Image attached</div>` : ""}
        </div>
        <div style="display:flex;gap:6px;flex-shrink:0">
          <button class="btn btn-secondary btn-sm edit-product" data-id="${p.id}" data-name="${esc(p.name)}" data-desc="${esc(p.description || "")}">Edit</button>
          <button class="btn btn-danger btn-sm delete-product" data-id="${p.id}">Delete</button>
        </div>
      </div>
      <!-- Inline edit form (hidden by default) -->
      <div class="edit-form" id="product-edit-${p.id}" style="display:none">
        <div class="form-group">
          <label>Product Name *</label>
          <input class="edit-p-name" data-id="${p.id}" value="${esc(p.name)}" required />
        </div>
        <div class="form-group">
          <label>Description</label>
          <textarea class="edit-p-desc" data-id="${p.id}">${esc(p.description || "")}</textarea>
        </div>
        <div class="edit-form-actions">
          <button class="btn btn-primary btn-sm save-product" data-id="${p.id}">Save</button>
          <button class="btn btn-secondary btn-sm cancel-edit-product" data-id="${p.id}">Cancel</button>
        </div>
        <div class="error-msg edit-product-error" data-id="${p.id}"></div>
      </div>
    </div>
  `).join("") || `<div class="empty-state"><p>No products yet.</p></div>`;

  return `
    ${cards}
    <div class="card">
      <div class="card-title mb-8">Add Product</div>
      <form id="product-form">
        <div class="grid-2">
          <div class="form-group">
            <label>Product Name *</label>
            <input id="p-name" required placeholder="Ultra Foam Running Shoe" />
          </div>
          <div class="form-group">
            <label>Upload Image</label>
            <input type="file" id="p-image" accept="image/*" style="padding:6px" />
          </div>
        </div>
        <div class="form-group">
          <label>Description</label>
          <textarea id="p-desc" placeholder="Describe the product, materials, use cases, key features..."></textarea>
        </div>
        <button type="submit" class="btn btn-primary btn-sm">Add Product</button>
        <div class="error-msg" id="product-error"></div>
      </form>
    </div>
  `;
}

function renderPersonasTab(personas) {
  const cards = personas.map(p => {
    const traits = p.traits || {};
    return `
    <div class="card" style="cursor:default" id="persona-card-${p.id}">
      <div class="persona-card">
        <div class="persona-avatar">👤</div>
        <div style="flex:1">
          <div class="card-title">${esc(p.name)}</div>
          <div class="card-meta">${Object.entries(traits).slice(0,3).map(([k,v])=>`${k}: ${v}`).join(" · ") || "No traits defined"}</div>
        </div>
        <div style="display:flex;gap:6px;flex-shrink:0">
          <button class="btn btn-secondary btn-sm edit-persona" data-id="${p.id}">Edit</button>
          <button class="btn btn-danger btn-sm delete-persona" data-id="${p.id}">Delete</button>
        </div>
      </div>
      <!-- Inline edit form -->
      <div class="edit-form" id="persona-edit-${p.id}" style="display:none">
        <div class="grid-2">
          <div class="form-group">
            <label>Persona Name *</label>
            <input class="edit-pe-name" data-id="${p.id}" value="${esc(p.name)}" required />
          </div>
          <div class="form-group">
            <label>Age Range</label>
            <input class="edit-pe-age" data-id="${p.id}" value="${esc(traits.age_range || "")}" />
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Gender Expression</label>
            <input class="edit-pe-gender" data-id="${p.id}" value="${esc(traits.gender_expression || "")}" />
          </div>
          <div class="form-group">
            <label>Fashion Style</label>
            <input class="edit-pe-fashion" data-id="${p.id}" value="${esc(traits.fashion_style || "")}" />
          </div>
        </div>
        <div class="form-group">
          <label>Voice & Tone</label>
          <input class="edit-pe-voice" data-id="${p.id}" value="${esc(traits.voice_tone || "")}" />
        </div>
        <div class="form-group">
          <label>Beliefs & Values</label>
          <input class="edit-pe-beliefs" data-id="${p.id}" value="${esc(traits.beliefs || "")}" />
        </div>
        <div class="edit-form-actions">
          <button class="btn btn-primary btn-sm save-persona" data-id="${p.id}">Save</button>
          <button class="btn btn-secondary btn-sm cancel-edit-persona" data-id="${p.id}">Cancel</button>
        </div>
        <div class="error-msg edit-persona-error" data-id="${p.id}"></div>
      </div>
    </div>
  `}).join("") || `<div class="empty-state"><p>No personas yet.</p></div>`;

  return `
    ${cards}
    <div class="card">
      <div class="card-title mb-8">Add Persona</div>
      <form id="persona-form">
        <div class="grid-2">
          <div class="form-group">
            <label>Persona Name *</label>
            <input id="pe-name" required placeholder="Alex — Urban Athlete" />
          </div>
          <div class="form-group">
            <label>Age Range</label>
            <input id="pe-age" placeholder="25-34" />
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Gender Expression</label>
            <input id="pe-gender" placeholder="Feminine / Masculine / Androgynous" />
          </div>
          <div class="form-group">
            <label>Fashion Style</label>
            <input id="pe-fashion" placeholder="Minimalist athletic" />
          </div>
        </div>
        <div class="form-group">
          <label>Voice & Tone</label>
          <input id="pe-voice" placeholder="Confident, direct, aspirational" />
        </div>
        <div class="form-group">
          <label>Beliefs & Values</label>
          <input id="pe-beliefs" placeholder="Performance, sustainability, urban lifestyle" />
        </div>
        <button type="submit" class="btn btn-primary btn-sm">Add Persona</button>
        <div class="error-msg" id="persona-error"></div>
      </form>
    </div>
  `;
}

function renderConfigTab(campaign) {
  const channels = campaign.target_channels ? JSON.parse(campaign.target_channels) : [];
  return `
    <div class="card">
      <div class="card-title mb-8">Campaign Configuration</div>
      <form id="config-form">
        <div class="form-group">
          <label>Target Channels</label>
          <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:4px">
            ${["meta", "tiktok", "youtube"].map(ch => `
              <label class="checkbox-label">
                <input type="checkbox" name="channel" value="${ch}" ${channels.includes(ch) ? "checked" : ""} />
                ${ch.charAt(0).toUpperCase() + ch.slice(1)}
              </label>
            `).join("")}
          </div>
        </div>
        <div class="form-group">
          <label>Campaign Notes</label>
          <textarea id="cfg-notes" placeholder="Additional context or special instructions…">${esc(campaign.campaign_notes || "")}</textarea>
        </div>
        <button type="submit" class="btn btn-primary btn-sm">Save Config</button>
        <div class="error-msg" id="config-error"></div>
      </form>
    </div>
  `;
}

function _adName(a, products) {
  const product = products.find(p => p.id === a.product_id);
  const productName = product ? product.name : "Unknown Product";
  const slogan = a.marketing_output?.product_slogan;
  return slogan ? `${productName} · "${slogan.slice(0, 40)}${slogan.length > 40 ? "…" : ""}"` : `${productName} Ad`;
}

function renderAdsTab(ads, products) {
  const sorted = [...ads].sort((a, b) =>
    _adSortDir === "desc"
      ? new Date(b.created_at) - new Date(a.created_at)
      : new Date(a.created_at) - new Date(b.created_at)
  );
  const cards = sorted.length
    ? sorted.map(a => `
      <div class="card" id="ad-card-${a.id}" style="cursor:pointer" data-ad-id="${a.id}">
        <div style="display:flex;align-items:center;gap:12px">
          <div style="flex:1;min-width:0" onclick="window.location.hash='#generate/${_campaignId}/${a.id}'">
            <div class="card-title" style="margin-bottom:2px">${esc(_adName(a, products))}</div>
            <div class="card-meta" style="font-size:11px;font-family:monospace;color:var(--text-muted)">${a.id}</div>
            <div class="card-meta" style="margin-top:4px">
              <span class="badge badge-${statusBadge(a.status)}">${a.status}</span>
              ${a.target_channel ? `<span class="badge badge-channel" style="margin-left:4px">${a.target_channel}</span>` : ""}
              <span style="margin-left:8px;font-size:11px;color:var(--text-muted)">${fmtDT(a.created_at)}</span>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0">
            ${a.image_url ? `<img src="${a.image_url}" style="height:56px;border-radius:6px" onclick="window.location.hash='#generate/${_campaignId}/${a.id}'" />` : ""}
            <button class="btn btn-danger btn-sm delete-ad" data-id="${a.id}">Delete</button>
          </div>
        </div>
      </div>
    `).join("")
    : `<div class="empty-state"><p>No advertisements generated yet.</p></div>`;

  return `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <button class="btn btn-secondary btn-sm" id="ad-sort-btn" style="font-size:11px">
        Sort: ${_adSortDir === "desc" ? "Newest first" : "Oldest first"}
      </button>
      <div class="form-group" style="margin:0;display:flex;align-items:center;gap:6px">
        <label style="font-size:11px;white-space:nowrap;margin:0">Filter date:</label>
        <input type="date" id="ad-filter-date" class="btn btn-secondary btn-sm" style="font-size:11px;padding:4px 8px;cursor:pointer" />
        <button class="btn btn-secondary btn-sm" id="ad-filter-clear" style="font-size:11px">Clear</button>
      </div>
    </div>
    <div id="ads-list">${cards}</div>
  `;
}

export function bindProject(campaignId) {
  _campaignId = campaignId;

  document.getElementById("go-generate-btn")?.addEventListener("click", () => {
    window.location.hash = `#generate/${campaignId}`;
  });

  // Tab switching
  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      ["products", "personas", "ads", "config"].forEach(name => {
        const el = document.getElementById(`tab-${name}`);
        if (el) el.style.display = tab.dataset.tab === name ? "block" : "none";
      });
    });
  });

  // Campaign config form
  document.getElementById("config-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("[type=submit]");
    btn.disabled = true;
    document.getElementById("config-error").textContent = "";
    try {
      const selectedChannels = [...document.querySelectorAll('input[name="channel"]:checked')].map(cb => cb.value);
      await api.updateCampaign(campaignId, {
        target_channels: JSON.stringify(selectedChannels),
        campaign_notes: document.getElementById("cfg-notes").value.trim() || null,
      });
      btn.textContent = "Saved!";
      setTimeout(() => { btn.textContent = "Save Config"; btn.disabled = false; }, 1500);
    } catch (err) {
      document.getElementById("config-error").textContent = err.message;
      btn.disabled = false;
    }
  });

  // Product form
  document.getElementById("product-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("[type=submit]");
    btn.disabled = true;
    document.getElementById("product-error").textContent = "";
    try {
      const product = await api.createProduct(campaignId, {
        name: document.getElementById("p-name").value.trim(),
        description: document.getElementById("p-desc").value.trim() || null,
      });
      const imageFile = document.getElementById("p-image").files[0];
      if (imageFile) {
        await api.uploadImage(campaignId, product.id, imageFile);
      }
      window.location.reload();
    } catch (err) {
      document.getElementById("product-error").textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });

  // Persona form
  document.getElementById("persona-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("[type=submit]");
    btn.disabled = true;
    document.getElementById("persona-error").textContent = "";
    try {
      const traits = {};
      const age = document.getElementById("pe-age").value.trim();
      const gender = document.getElementById("pe-gender").value.trim();
      const fashion = document.getElementById("pe-fashion").value.trim();
      const voice = document.getElementById("pe-voice").value.trim();
      const beliefs = document.getElementById("pe-beliefs").value.trim();
      if (age) traits.age_range = age;
      if (gender) traits.gender_expression = gender;
      if (fashion) traits.fashion_style = fashion;
      if (voice) traits.voice_tone = voice;
      if (beliefs) traits.beliefs = beliefs;
      await api.createPersona(campaignId, {
        name: document.getElementById("pe-name").value.trim(),
        traits: Object.keys(traits).length ? traits : null,
      });
      window.location.reload();
    } catch (err) {
      document.getElementById("persona-error").textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });

  // Delete handlers
  document.querySelectorAll(".delete-product").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm("Delete this product?")) return;
      await api.deleteProduct(campaignId, btn.dataset.id);
      window.location.reload();
    });
  });
  document.querySelectorAll(".delete-persona").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm("Delete this persona?")) return;
      await api.deletePersona(campaignId, btn.dataset.id);
      window.location.reload();
    });
  });

  // Edit product handlers
  document.querySelectorAll(".edit-product").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const form = document.getElementById(`product-edit-${id}`);
      if (form) form.style.display = form.style.display === "none" ? "block" : "none";
    });
  });
  document.querySelectorAll(".cancel-edit-product").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      document.getElementById(`product-edit-${btn.dataset.id}`).style.display = "none";
    });
  });
  document.querySelectorAll(".save-product").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const nameEl = document.querySelector(`.edit-p-name[data-id="${id}"]`);
      const descEl = document.querySelector(`.edit-p-desc[data-id="${id}"]`);
      const errEl = document.querySelector(`.edit-product-error[data-id="${id}"]`);
      if (!nameEl.value.trim()) { if (errEl) errEl.textContent = "Name is required"; return; }
      btn.disabled = true;
      try {
        await api.updateProduct(campaignId, id, {
          name: nameEl.value.trim(),
          description: descEl.value.trim() || null,
        });
        window.location.reload();
      } catch (err) {
        if (errEl) errEl.textContent = err.message;
        btn.disabled = false;
      }
    });
  });

  // Edit persona handlers
  document.querySelectorAll(".edit-persona").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const form = document.getElementById(`persona-edit-${id}`);
      if (form) form.style.display = form.style.display === "none" ? "block" : "none";
    });
  });
  document.querySelectorAll(".cancel-edit-persona").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      document.getElementById(`persona-edit-${btn.dataset.id}`).style.display = "none";
    });
  });
  document.querySelectorAll(".save-persona").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const nameEl = document.querySelector(`.edit-pe-name[data-id="${id}"]`);
      const errEl  = document.querySelector(`.edit-persona-error[data-id="${id}"]`);
      if (!nameEl.value.trim()) { if (errEl) errEl.textContent = "Name is required"; return; }
      btn.disabled = true;
      try {
        const traits = {};
        const age     = document.querySelector(`.edit-pe-age[data-id="${id}"]`).value.trim();
        const gender  = document.querySelector(`.edit-pe-gender[data-id="${id}"]`).value.trim();
        const fashion = document.querySelector(`.edit-pe-fashion[data-id="${id}"]`).value.trim();
        const voice   = document.querySelector(`.edit-pe-voice[data-id="${id}"]`).value.trim();
        const beliefs = document.querySelector(`.edit-pe-beliefs[data-id="${id}"]`).value.trim();
        if (age)     traits.age_range = age;
        if (gender)  traits.gender_expression = gender;
        if (fashion) traits.fashion_style = fashion;
        if (voice)   traits.voice_tone = voice;
        if (beliefs) traits.beliefs = beliefs;
        await api.updatePersona(campaignId, id, {
          name: nameEl.value.trim(),
          traits: Object.keys(traits).length ? traits : null,
        });
        window.location.reload();
      } catch (err) {
        if (errEl) errEl.textContent = err.message;
        btn.disabled = false;
      }
    });
  });

  // Ads tab — sort, filter, delete
  _bindAdControls(campaignId);
}

function _bindAdControls(campaignId) {
  document.getElementById("ad-sort-btn")?.addEventListener("click", () => {
    _adSortDir = _adSortDir === "desc" ? "asc" : "desc";
    _refreshAds();
  });
  document.getElementById("ad-filter-date")?.addEventListener("change", () => _refreshAds());
  document.getElementById("ad-filter-clear")?.addEventListener("click", () => {
    const el = document.getElementById("ad-filter-date");
    if (el) el.value = "";
    _refreshAds();
  });
  // Use event delegation for delete buttons (they may be re-rendered)
  document.getElementById("tab-ads")?.addEventListener("click", async (e) => {
    const btn = e.target.closest(".delete-ad");
    if (!btn) return;
    e.stopPropagation();
    const id = btn.dataset.id;
    if (!confirm("Delete this advertisement? This cannot be undone.")) return;
    btn.disabled = true;
    try {
      await api.deleteAdvertisement(campaignId, id);
      _allAds = _allAds.filter(a => a.id !== id);
      _refreshAds();
    } catch (err) {
      alert("Delete failed: " + err.message);
      btn.disabled = false;
    }
  });
}

function _refreshAds() {
  const dateVal = document.getElementById("ad-filter-date")?.value || "";
  let filtered = _allAds;
  if (dateVal) {
    filtered = filtered.filter(a => {
      const d = new Date(a.created_at);
      return d.toISOString().slice(0, 10) === dateVal;
    });
  }
  const sortBtn = document.getElementById("ad-sort-btn");
  if (sortBtn) sortBtn.textContent = `Sort: ${_adSortDir === "desc" ? "Newest first" : "Oldest first"}`;

  const sorted = [...filtered].sort((a, b) =>
    _adSortDir === "desc"
      ? new Date(b.created_at) - new Date(a.created_at)
      : new Date(a.created_at) - new Date(b.created_at)
  );
  const list = document.getElementById("ads-list");
  if (!list) return;
  if (!sorted.length) {
    list.innerHTML = `<div class="empty-state"><p>No advertisements match.</p></div>`;
    return;
  }
  list.innerHTML = sorted.map(a => `
    <div class="card" id="ad-card-${a.id}" style="cursor:pointer" data-ad-id="${a.id}">
      <div style="display:flex;align-items:center;gap:12px">
        <div style="flex:1;min-width:0" onclick="window.location.hash='#generate/${_campaignId}/${a.id}'">
          <div class="card-title" style="margin-bottom:2px">${esc(_adName(a, _allProducts))}</div>
          <div class="card-meta" style="font-size:11px;font-family:monospace;color:var(--text-muted)">${a.id}</div>
          <div class="card-meta" style="margin-top:4px">
            <span class="badge badge-${statusBadge(a.status)}">${a.status}</span>
            ${a.target_channel ? `<span class="badge badge-channel" style="margin-left:4px">${a.target_channel}</span>` : ""}
            <span style="margin-left:8px;font-size:11px;color:var(--text-muted)">${fmtDT(a.created_at)}</span>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0">
          ${a.image_url ? `<img src="${a.image_url}" style="height:56px;border-radius:6px" onclick="window.location.hash='#generate/${_campaignId}/${a.id}'" />` : ""}
          <button class="btn btn-danger btn-sm delete-ad" data-id="${a.id}">Delete</button>
        </div>
      </div>
    </div>
  `).join("");
}

function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
function fmt(dt) { return new Date(dt).toLocaleDateString(); }
function fmtDT(dt) {
  const d = new Date(dt);
  const date = d.toLocaleDateString();
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  return `${date} ${time}`;
}
function statusBadge(s) {
  if (s === "completed") return "success";
  if (s === "failed" || s === "partial_failure") return "error";
  return "warning";
}
