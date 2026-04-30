import { api } from "./api.js";

let _brandId = null;

export async function renderBrands(brandId = null) {
  _brandId = brandId;

  if (brandId) return renderBrandDetail(brandId);
  return renderBrandList();
}

async function renderBrandList() {
  let brands = [];
  try { brands = await api.getBrands(); } catch {}

  const cards = brands.length
    ? brands.map(b => `
        <div class="card" data-id="${b.id}" style="cursor:pointer">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
              <div class="card-title">${esc(b.name)}</div>
              ${b.company ? `<div class="card-meta">${esc(b.company)}</div>` : ""}
              ${b.mission ? `<div class="card-meta mt-8" style="margin-top:4px">${esc(b.mission.slice(0, 80))}${b.mission.length > 80 ? "…" : ""}</div>` : ""}
            </div>
            <button class="btn btn-secondary btn-sm delete-brand" data-id="${b.id}">Delete</button>
          </div>
        </div>
      `).join("")
    : `<div class="empty-state"><p>No brand profiles yet. Create one to enable brand consistency and reuse across campaigns.</p></div>`;

  return `
    <div class="page">
      <div class="section-header">
        <h1 class="page-title" style="margin-bottom:0">Brand Brain</h1>
        <button class="btn btn-primary btn-sm" id="new-brand-btn">+ New Brand</button>
      </div>
      <div id="brand-list">${cards}</div>

      <div id="brand-form-wrap" style="display:none">
        <hr />
        <div class="card">
          <div class="card-title mb-8">New Brand Profile</div>
          <form id="brand-form">
            <div class="grid-2">
              <div class="form-group">
                <label>Brand Name *</label>
                <input id="b-name" required placeholder="Acme Running Co." />
              </div>
              <div class="form-group">
                <label>Company Name</label>
                <input id="b-company" placeholder="Acme Corp." />
              </div>
            </div>
            <div class="form-group">
              <label>Mission Statement</label>
              <textarea id="b-mission" placeholder="We make gear for athletes who refuse to slow down."></textarea>
            </div>
            <div class="form-group">
              <label>Brand Values</label>
              <input id="b-values" placeholder="Performance, sustainability, accessibility" />
            </div>
            <div class="form-group">
              <label>Brand Guidelines</label>
              <textarea id="b-guidelines" placeholder="Minimalist design, bold typography, never use stock photos…"></textarea>
            </div>
            <div class="form-group">
              <label>Tone Keywords</label>
              <input id="b-tone" placeholder="Energetic, direct, aspirational, no fluff" />
            </div>
            <div style="display:flex;gap:8px">
              <button type="submit" class="btn btn-primary">Create</button>
              <button type="button" class="btn btn-secondary" id="cancel-brand">Cancel</button>
            </div>
            <div class="error-msg" id="brand-error"></div>
          </form>
        </div>
      </div>
    </div>
  `;
}

async function renderBrandDetail(brandId) {
  let brand, products = [], personas = [];
  try {
    [brand, products, personas] = await Promise.all([
      api.getBrand(brandId),
      api.getBrandProducts(brandId),
      api.getBrandPersonas(brandId),
    ]);
  } catch (e) {
    return `<div class="page"><p class="text-muted">Failed to load brand: ${e.message}</p></div>`;
  }

  return `
    <div class="page">
      <a href="#brands" style="color:var(--text-muted);font-size:12px;text-decoration:none">← Brand Brain</a>
      <h1 class="page-title" style="margin-top:8px">${esc(brand.name)}</h1>

      <div class="tabs" id="brand-tabs">
        <div class="tab active" data-tab="overview">Overview</div>
        <div class="tab" data-tab="products">Products (${products.length})</div>
        <div class="tab" data-tab="personas">Personas (${personas.length})</div>
      </div>

      <div id="tab-overview">${renderOverviewTab(brand)}</div>
      <div id="tab-products" style="display:none">${renderBrandProductsTab(products)}</div>
      <div id="tab-personas" style="display:none">${renderBrandPersonasTab(personas)}</div>
    </div>
  `;
}

function renderOverviewTab(brand) {
  return `
    <div class="card">
      <form id="brand-edit-form">
        <div class="grid-2">
          <div class="form-group">
            <label>Brand Name</label>
            <input id="be-name" value="${esc(brand.name)}" required />
          </div>
          <div class="form-group">
            <label>Company</label>
            <input id="be-company" value="${esc(brand.company || "")}" placeholder="Company name" />
          </div>
        </div>
        <div class="form-group">
          <label>Mission</label>
          <textarea id="be-mission">${esc(brand.mission || "")}</textarea>
        </div>
        <div class="form-group">
          <label>Values</label>
          <input id="be-values" value="${esc(brand.values || "")}" placeholder="Comma-separated values" />
        </div>
        <div class="form-group">
          <label>Brand Guidelines</label>
          <textarea id="be-guidelines">${esc(brand.brand_guidelines || "")}</textarea>
        </div>
        <div class="form-group">
          <label>Tone Keywords</label>
          <input id="be-tone" value="${esc(brand.tone_keywords || "")}" placeholder="Comma-separated tone words" />
        </div>
        <button type="submit" class="btn btn-primary btn-sm">Save Changes</button>
        <div class="error-msg" id="brand-edit-error"></div>
      </form>
    </div>
  `;
}

function renderBrandProductsTab(products) {
  const cards = products.map(p => `
    <div class="card" style="cursor:default">
      <div style="display:flex;justify-content:space-between">
        <div>
          <div class="card-title">${esc(p.name)}</div>
          <div class="card-meta">${esc(p.description || "No description")}</div>
        </div>
        <button class="btn btn-secondary btn-sm delete-bp" data-id="${p.id}">Delete</button>
      </div>
    </div>
  `).join("") || `<div class="empty-state"><p>No products yet.</p></div>`;

  return `
    ${cards}
    <div class="card">
      <div class="card-title mb-8">Add Product</div>
      <form id="bp-form">
        <div class="grid-2">
          <div class="form-group">
            <label>Product Name *</label>
            <input id="bp-name" required placeholder="Ultra Foam Shoe" />
          </div>
          <div class="form-group">
            <label>Upload Image</label>
            <input type="file" id="bp-image" accept="image/*" style="padding:6px" />
          </div>
        </div>
        <div class="form-group">
          <label>Description</label>
          <textarea id="bp-desc" placeholder="Product details, materials, use cases…"></textarea>
        </div>
        <button type="submit" class="btn btn-primary btn-sm">Add Product</button>
        <div class="error-msg" id="bp-error"></div>
      </form>
    </div>
  `;
}

function renderBrandPersonasTab(personas) {
  const cards = personas.map(p => `
    <div class="card" style="cursor:default">
      <div class="persona-card">
        <div class="persona-avatar">👤</div>
        <div style="flex:1">
          <div class="card-title">${esc(p.name)}</div>
          <div class="card-meta">${p.traits ? Object.entries(p.traits).slice(0,3).map(([k,v])=>`${k}: ${v}`).join(" · ") : "No traits"}</div>
        </div>
        <button class="btn btn-secondary btn-sm delete-bpe" data-id="${p.id}">Delete</button>
      </div>
    </div>
  `).join("") || `<div class="empty-state"><p>No personas yet.</p></div>`;

  return `
    ${cards}
    <div class="card">
      <div class="card-title mb-8">Add Persona</div>
      <form id="bpe-form">
        <div class="grid-2">
          <div class="form-group">
            <label>Persona Name *</label>
            <input id="bpe-name" required placeholder="Alex — Urban Athlete" />
          </div>
          <div class="form-group">
            <label>Age Range</label>
            <input id="bpe-age" placeholder="25-34" />
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Gender Expression</label>
            <input id="bpe-gender" placeholder="Feminine / Masculine / Androgynous" />
          </div>
          <div class="form-group">
            <label>Fashion Style</label>
            <input id="bpe-fashion" placeholder="Minimalist athletic" />
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Voice & Tone</label>
            <input id="bpe-voice" placeholder="Confident, direct" />
          </div>
          <div class="form-group">
            <label>Beliefs & Values</label>
            <input id="bpe-beliefs" placeholder="Performance, urban lifestyle" />
          </div>
        </div>
        <button type="submit" class="btn btn-primary btn-sm">Add Persona</button>
        <div class="error-msg" id="bpe-error"></div>
      </form>
    </div>
  `;
}

export function bindBrands(brandId = null) {
  _brandId = brandId;

  if (brandId) {
    bindBrandDetail(brandId);
    return;
  }

  document.getElementById("new-brand-btn")?.addEventListener("click", () => {
    document.getElementById("brand-form-wrap").style.display = "block";
    document.getElementById("new-brand-btn").style.display = "none";
  });

  document.getElementById("cancel-brand")?.addEventListener("click", () => {
    document.getElementById("brand-form-wrap").style.display = "none";
    document.getElementById("new-brand-btn").style.display = "";
  });

  document.getElementById("brand-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("[type=submit]");
    btn.disabled = true;
    document.getElementById("brand-error").textContent = "";
    try {
      const brand = await api.createBrand({
        name: document.getElementById("b-name").value.trim(),
        company: document.getElementById("b-company").value.trim() || null,
        mission: document.getElementById("b-mission").value.trim() || null,
        values: document.getElementById("b-values").value.trim() || null,
        brand_guidelines: document.getElementById("b-guidelines").value.trim() || null,
        tone_keywords: document.getElementById("b-tone").value.trim() || null,
      });
      window.location.hash = `#brands/${brand.id}`;
    } catch (err) {
      document.getElementById("brand-error").textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });

  document.querySelectorAll(".card[data-id]").forEach(card => {
    card.addEventListener("click", (e) => {
      if (e.target.classList.contains("delete-brand")) return;
      window.location.hash = `#brands/${card.dataset.id}`;
    });
  });

  document.querySelectorAll(".delete-brand").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm("Delete this brand profile?")) return;
      await api.deleteBrand(btn.dataset.id);
      window.location.reload();
    });
  });
}

function bindBrandDetail(brandId) {
  // Tab switching
  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      ["overview", "products", "personas"].forEach(name => {
        document.getElementById(`tab-${name}`).style.display = tab.dataset.tab === name ? "block" : "none";
      });
    });
  });

  // Edit form
  document.getElementById("brand-edit-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("[type=submit]");
    btn.disabled = true;
    document.getElementById("brand-edit-error").textContent = "";
    try {
      await api.updateBrand(brandId, {
        name: document.getElementById("be-name").value.trim(),
        company: document.getElementById("be-company").value.trim() || null,
        mission: document.getElementById("be-mission").value.trim() || null,
        values: document.getElementById("be-values").value.trim() || null,
        brand_guidelines: document.getElementById("be-guidelines").value.trim() || null,
        tone_keywords: document.getElementById("be-tone").value.trim() || null,
      });
      btn.textContent = "Saved!";
      setTimeout(() => { btn.textContent = "Save Changes"; btn.disabled = false; }, 1500);
    } catch (err) {
      document.getElementById("brand-edit-error").textContent = err.message;
      btn.disabled = false;
    }
  });

  // Brand product form
  document.getElementById("bp-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("[type=submit]");
    btn.disabled = true;
    document.getElementById("bp-error").textContent = "";
    try {
      const prod = await api.createBrandProduct(brandId, {
        name: document.getElementById("bp-name").value.trim(),
        description: document.getElementById("bp-desc").value.trim() || null,
      });
      const img = document.getElementById("bp-image").files[0];
      if (img) await api.uploadBrandProductImage(brandId, prod.id, img);
      window.location.reload();
    } catch (err) {
      document.getElementById("bp-error").textContent = err.message;
      btn.disabled = false;
    }
  });

  document.querySelectorAll(".delete-bp").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this product?")) return;
      await api.deleteBrandProduct(brandId, btn.dataset.id);
      window.location.reload();
    });
  });

  // Brand persona form
  document.getElementById("bpe-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("[type=submit]");
    btn.disabled = true;
    document.getElementById("bpe-error").textContent = "";
    try {
      const traits = {};
      const age = document.getElementById("bpe-age").value.trim();
      const gender = document.getElementById("bpe-gender").value.trim();
      const fashion = document.getElementById("bpe-fashion").value.trim();
      const voice = document.getElementById("bpe-voice").value.trim();
      const beliefs = document.getElementById("bpe-beliefs").value.trim();
      if (age) traits.age_range = age;
      if (gender) traits.gender_expression = gender;
      if (fashion) traits.fashion_style = fashion;
      if (voice) traits.voice_tone = voice;
      if (beliefs) traits.beliefs = beliefs;
      await api.createBrandPersona(brandId, {
        name: document.getElementById("bpe-name").value.trim(),
        traits: Object.keys(traits).length ? traits : null,
      });
      window.location.reload();
    } catch (err) {
      document.getElementById("bpe-error").textContent = err.message;
      btn.disabled = false;
    }
  });

  document.querySelectorAll(".delete-bpe").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this persona?")) return;
      await api.deleteBrandPersona(brandId, btn.dataset.id);
      window.location.reload();
    });
  });
}

function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
