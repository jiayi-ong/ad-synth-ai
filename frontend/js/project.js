import { api } from "./api.js";

let _campaignId = null;

export async function renderProject(campaignId) {
  _campaignId = campaignId;
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
      </div>

      <div id="tab-products">${renderProductsTab(products)}</div>
      <div id="tab-personas" style="display:none">${renderPersonasTab(personas)}</div>
      <div id="tab-ads" style="display:none">${renderAdsTab(ads)}</div>
    </div>
  `;
}

function renderProductsTab(products) {
  const cards = products.map(p => `
    <div class="card" style="cursor:default">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
          <div class="card-title">${esc(p.name)}</div>
          <div class="card-meta">${esc(p.description || "No description")}</div>
          ${p.image_path ? `<div class="card-meta mt-16">📎 Image attached</div>` : ""}
        </div>
        <button class="btn btn-secondary btn-sm delete-product" data-id="${p.id}">Delete</button>
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
  const cards = personas.map(p => `
    <div class="card" style="cursor:default">
      <div class="persona-card">
        <div class="persona-avatar">👤</div>
        <div style="flex:1">
          <div class="card-title">${esc(p.name)}</div>
          <div class="card-meta">${p.traits ? Object.entries(p.traits).slice(0,3).map(([k,v])=>`${k}: ${v}`).join(" · ") : "No traits defined"}</div>
        </div>
        <button class="btn btn-secondary btn-sm delete-persona" data-id="${p.id}">Delete</button>
      </div>
    </div>
  `).join("") || `<div class="empty-state"><p>No personas yet.</p></div>`;

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

function renderAdsTab(ads) {
  if (!ads.length) return `<div class="empty-state"><p>No advertisements generated yet.</p></div>`;
  return ads.map(a => `
    <div class="card" style="cursor:pointer" data-ad-id="${a.id}" onclick="window.location.hash='#generate/${_campaignId}/${a.id}'">
      <div style="display:flex;align-items:center;gap:12px">
        <div>
          <div class="card-title">Ad · ${fmt(a.created_at)}</div>
          <div class="card-meta">Status: <span class="badge badge-${statusBadge(a.status)}">${a.status}</span></div>
        </div>
        ${a.image_url ? `<img src="${a.image_url}" style="height:60px;border-radius:6px;margin-left:auto">` : ""}
      </div>
    </div>
  `).join("");
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
      ["products", "personas", "ads"].forEach(name => {
        document.getElementById(`tab-${name}`).style.display = tab.dataset.tab === name ? "block" : "none";
      });
    });
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
}

function esc(s) { return (s || "").replace(/</g, "&lt;"); }
function fmt(dt) { return new Date(dt).toLocaleDateString(); }
function statusBadge(s) {
  if (s === "completed") return "success";
  if (s === "failed" || s === "partial_failure") return "error";
  return "warning";
}
