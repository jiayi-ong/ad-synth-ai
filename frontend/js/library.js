import { api } from "./api.js";

let _ads = [];
let _filterChannel = "";
let _filterStatus = "";

export async function renderLibrary() {
  let campaigns = [];
  try { campaigns = await api.getCampaigns(); } catch {}

  // Fetch ads from all campaigns
  const adGroups = await Promise.allSettled(
    campaigns.map(c => api.getAdvertisements(c.id).then(ads => ads.map(a => ({ ...a, campaign_name: c.name }))))
  );
  _ads = adGroups.flatMap(r => r.status === "fulfilled" ? r.value : []);
  _ads.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  return `
    <div class="page">
      <div class="section-header">
        <h1 class="page-title" style="margin-bottom:0">Ad Library</h1>
        <div style="display:flex;gap:8px">
          <select id="filter-channel" class="btn btn-secondary btn-sm" style="padding:6px 10px;cursor:pointer">
            <option value="">All Channels</option>
            <option value="meta">Meta</option>
            <option value="tiktok">TikTok</option>
            <option value="youtube">YouTube</option>
          </select>
          <select id="filter-status" class="btn btn-secondary btn-sm" style="padding:6px 10px;cursor:pointer">
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="generating">Generating</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      <div id="library-grid" class="ad-library-grid">
        ${renderGrid(_ads)}
      </div>
    </div>
  `;
}

function renderGrid(ads) {
  if (!ads.length) return `<div class="empty-state"><p>No ads yet. Generate your first ad from a campaign.</p></div>`;
  return ads.map(a => `
    <div class="ad-library-card" onclick="window.location.hash='#generate/${a.campaign_id}/${a.id}'">
      <div class="ad-library-thumb">
        ${a.image_url
          ? `<img src="${a.image_url}" alt="Ad preview">`
          : `<div class="ad-thumb-placeholder">No image</div>`}
      </div>
      <div class="ad-library-info">
        <div class="card-title" style="font-size:13px">${esc(a.campaign_name || "Campaign")}</div>
        <div class="card-meta">${fmt(a.created_at)}</div>
        <div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap">
          <span class="badge badge-${statusBadge(a.status)}">${a.status}</span>
          ${a.target_channel ? `<span class="badge badge-channel">${a.target_channel}</span>` : ""}
          ${a.brand_consistency_score != null ? `<span class="badge badge-warning">Brand ${Math.round(a.brand_consistency_score * 100)}%</span>` : ""}
        </div>
        ${a.evaluation_output?.overall_score != null
          ? `<div class="text-muted" style="font-size:11px;margin-top:4px">Score: ${a.evaluation_output.overall_score}/10</div>`
          : ""}
      </div>
    </div>
  `).join("");
}

export function bindLibrary() {
  document.getElementById("filter-channel")?.addEventListener("change", e => {
    _filterChannel = e.target.value;
    applyFilters();
  });
  document.getElementById("filter-status")?.addEventListener("change", e => {
    _filterStatus = e.target.value;
    applyFilters();
  });
}

function applyFilters() {
  let filtered = _ads;
  if (_filterChannel) filtered = filtered.filter(a => a.target_channel === _filterChannel);
  if (_filterStatus) filtered = filtered.filter(a => a.status === _filterStatus);
  document.getElementById("library-grid").innerHTML = renderGrid(filtered);
}

function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
function fmt(dt) { return new Date(dt).toLocaleDateString(); }
function statusBadge(s) {
  if (s === "completed") return "success";
  if (s === "failed" || s === "partial_failure") return "error";
  return "warning";
}
