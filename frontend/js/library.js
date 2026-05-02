import { api } from "./api.js";

let _ads = [];
let _campaigns = [];
let _filterChannel = "";
let _filterStatus = "";
let _filterCampaign = "";
let _filterDate = "";
let _sortDir = "desc";

export async function renderLibrary() {
  _campaigns = [];
  try { _campaigns = await api.getCampaigns(); } catch {}

  const adGroups = await Promise.allSettled(
    _campaigns.map(c => api.getAdvertisements(c.id).then(ads => ads.map(a => ({ ...a, campaign_name: c.name }))))
  );
  _ads = adGroups.flatMap(r => r.status === "fulfilled" ? r.value : []);
  _ads.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  const campaignOptions = _campaigns.map(c =>
    `<option value="${c.id}">${esc(c.name)}</option>`
  ).join("");

  return `
    <div class="page">
      <div class="section-header">
        <h1 class="page-title" style="margin-bottom:0">Ad Library</h1>
      </div>

      <!-- Filters + sort bar -->
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px">
        <button class="btn btn-secondary btn-sm" id="lib-sort-btn" style="font-size:11px">
          Sort: Newest first
        </button>
        <select id="filter-campaign" class="btn btn-secondary btn-sm" style="padding:6px 10px;cursor:pointer">
          <option value="">All Campaigns</option>
          ${campaignOptions}
        </select>
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
        <input type="date" id="filter-date" class="btn btn-secondary btn-sm" style="font-size:11px;padding:4px 8px;cursor:pointer" title="Filter by date" />
        <button class="btn btn-secondary btn-sm" id="lib-filter-clear" style="font-size:11px">Clear filters</button>
      </div>

      <div id="library-grid" class="ad-library-grid">
        ${_renderGrid(_ads)}
      </div>
    </div>
  `;
}

function _renderGrid(ads) {
  if (!ads.length) return `<div class="empty-state"><p>No ads match your filters.</p></div>`;
  return ads.map(a => `
    <div class="ad-library-card" data-ad-id="${a.id}" data-campaign-id="${a.campaign_id}">
      <div class="ad-library-thumb" onclick="window.location.hash='#generate/${a.campaign_id}/${a.id}'" style="cursor:pointer">
        ${a.image_url
          ? `<img src="${a.image_url}" alt="Ad preview">`
          : `<div class="ad-thumb-placeholder">No image</div>`}
      </div>
      <div class="ad-library-info">
        <div class="card-title" style="font-size:13px;cursor:pointer" onclick="window.location.hash='#generate/${a.campaign_id}/${a.id}'">${esc(a.campaign_name || "Campaign")}</div>
        <div class="card-meta" style="font-size:11px;color:var(--text-muted)">${fmtDT(a.created_at)}</div>
        <div class="card-meta" style="font-size:10px;font-family:monospace;color:var(--text-muted);margin-top:2px">${a.id}</div>
        <div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap">
          <span class="badge badge-${statusBadge(a.status)}">${a.status}</span>
          ${a.target_channel ? `<span class="badge badge-channel">${a.target_channel}</span>` : ""}
          ${a.brand_consistency_score != null ? `<span class="badge badge-warning">Brand ${Math.round(a.brand_consistency_score * 100)}%</span>` : ""}
        </div>
        ${a.evaluation_output?.overall_score != null
          ? `<div class="text-muted" style="font-size:11px;margin-top:4px">Score: ${a.evaluation_output.overall_score}/10</div>`
          : ""}
        <div style="margin-top:8px">
          <button class="btn btn-danger btn-sm lib-delete-ad" data-id="${a.id}" data-campaign-id="${a.campaign_id}" style="font-size:11px;width:100%">Delete</button>
        </div>
      </div>
    </div>
  `).join("");
}

export function bindLibrary() {
  document.getElementById("lib-sort-btn")?.addEventListener("click", () => {
    _sortDir = _sortDir === "desc" ? "asc" : "desc";
    document.getElementById("lib-sort-btn").textContent = `Sort: ${_sortDir === "desc" ? "Newest first" : "Oldest first"}`;
    _applyFilters();
  });

  document.getElementById("filter-campaign")?.addEventListener("change", e => {
    _filterCampaign = e.target.value;
    _applyFilters();
  });
  document.getElementById("filter-channel")?.addEventListener("change", e => {
    _filterChannel = e.target.value;
    _applyFilters();
  });
  document.getElementById("filter-status")?.addEventListener("change", e => {
    _filterStatus = e.target.value;
    _applyFilters();
  });
  document.getElementById("filter-date")?.addEventListener("change", e => {
    _filterDate = e.target.value;
    _applyFilters();
  });
  document.getElementById("lib-filter-clear")?.addEventListener("click", () => {
    _filterChannel = ""; _filterStatus = ""; _filterCampaign = ""; _filterDate = "";
    document.getElementById("filter-campaign").value = "";
    document.getElementById("filter-channel").value = "";
    document.getElementById("filter-status").value = "";
    document.getElementById("filter-date").value = "";
    _applyFilters();
  });

  // Delete via event delegation
  document.getElementById("library-grid")?.addEventListener("click", async (e) => {
    const btn = e.target.closest(".lib-delete-ad");
    if (!btn) return;
    e.stopPropagation();
    const id = btn.dataset.id;
    const campaignId = btn.dataset.campaignId;
    if (!confirm("Delete this advertisement? This cannot be undone.")) return;
    btn.disabled = true;
    try {
      await api.deleteAdvertisement(campaignId, id);
      _ads = _ads.filter(a => a.id !== id);
      _applyFilters();
    } catch (err) {
      alert("Delete failed: " + err.message);
      btn.disabled = false;
    }
  });
}

function _applyFilters() {
  let filtered = _ads;
  if (_filterCampaign) filtered = filtered.filter(a => a.campaign_id === _filterCampaign);
  if (_filterChannel) filtered = filtered.filter(a => a.target_channel === _filterChannel);
  if (_filterStatus) filtered = filtered.filter(a => a.status === _filterStatus);
  if (_filterDate) filtered = filtered.filter(a => new Date(a.created_at).toISOString().slice(0, 10) === _filterDate);
  filtered = [...filtered].sort((a, b) =>
    _sortDir === "desc"
      ? new Date(b.created_at) - new Date(a.created_at)
      : new Date(a.created_at) - new Date(b.created_at)
  );
  document.getElementById("library-grid").innerHTML = _renderGrid(filtered);
}

function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
function fmtDT(dt) {
  const d = new Date(dt);
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
}
function statusBadge(s) {
  if (s === "completed") return "success";
  if (s === "failed" || s === "partial_failure") return "error";
  return "warning";
}
