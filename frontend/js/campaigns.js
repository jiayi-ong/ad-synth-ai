import { api } from "./api.js";

export async function renderCampaigns() {
  let campaigns = [];
  try {
    campaigns = await api.getCampaigns();
  } catch {}

  const cards = campaigns.length
    ? campaigns.map(c => `
        <div class="card" data-id="${c.id}" id="campaign-${c.id}">
          <div class="card-title">${esc(c.name)}</div>
          <div class="card-meta">${esc(c.mission || "No mission set")} · Created ${fmt(c.created_at)}</div>
        </div>
      `).join("")
    : `<div class="empty-state"><p>No campaigns yet.</p></div>`;

  return `
    <div class="page">
      <div class="section-header">
        <h1 class="page-title" style="margin-bottom:0">Campaigns</h1>
        <button class="btn btn-primary btn-sm" id="new-campaign-btn">+ New Campaign</button>
      </div>
      <div id="campaign-list">${cards}</div>

      <div id="campaign-form-wrap" style="display:none">
        <hr />
        <div class="card">
          <div class="card-title mb-8">New Campaign</div>
          <form id="campaign-form">
            <div class="grid-2">
              <div class="form-group">
                <label>Campaign Name *</label>
                <input id="c-name" required placeholder="Summer 2026" />
              </div>
              <div class="form-group">
                <label>Brand Guidelines</label>
                <input id="c-brand" placeholder="Minimalist, bold, premium" />
              </div>
            </div>
            <div class="form-group">
              <label>Mission</label>
              <textarea id="c-mission" placeholder="What this campaign aims to achieve"></textarea>
            </div>
            <div class="form-group">
              <label>Values</label>
              <input id="c-values" placeholder="Innovation, sustainability, performance" />
            </div>
            <div style="display:flex;gap:8px">
              <button type="submit" class="btn btn-primary">Create</button>
              <button type="button" class="btn btn-secondary" id="cancel-campaign">Cancel</button>
            </div>
            <div class="error-msg" id="campaign-error"></div>
          </form>
        </div>
      </div>
    </div>
  `;
}

export function bindCampaigns() {
  document.getElementById("new-campaign-btn")?.addEventListener("click", () => {
    document.getElementById("campaign-form-wrap").style.display = "block";
    document.getElementById("new-campaign-btn").style.display = "none";
  });

  document.getElementById("cancel-campaign")?.addEventListener("click", () => {
    document.getElementById("campaign-form-wrap").style.display = "none";
    document.getElementById("new-campaign-btn").style.display = "";
  });

  document.getElementById("campaign-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("[type=submit]");
    btn.disabled = true;
    document.getElementById("campaign-error").textContent = "";
    try {
      const campaign = await api.createCampaign({
        name: document.getElementById("c-name").value.trim(),
        mission: document.getElementById("c-mission").value.trim() || null,
        values: document.getElementById("c-values").value.trim() || null,
        brand_guidelines: document.getElementById("c-brand").value.trim() || null,
      });
      window.location.hash = `#project/${campaign.id}`;
    } catch (err) {
      document.getElementById("campaign-error").textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });

  document.querySelectorAll(".card[data-id]").forEach(card => {
    card.addEventListener("click", () => {
      window.location.hash = `#project/${card.dataset.id}`;
    });
  });
}

function esc(s) { return (s || "").replace(/</g, "&lt;"); }
function fmt(dt) { return new Date(dt).toLocaleDateString(); }
