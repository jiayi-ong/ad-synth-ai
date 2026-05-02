// Per-stage structured data renderers for the wheel chart expand panel.
// Each renderer returns an HTML string.

export function renderStageData(key, data) {
  if (!data || (typeof data === "object" && data.error)) {
    return `<div class="text-muted" style="font-size:13px">${esc(data?.error || "No data")}</div>`;
  }
  try {
    switch (key) {
      case "product_profile":     return renderProductProfile(data);
      case "audience_analysis":   return renderAudienceAnalysis(data);
      case "trend_research":      return renderTrendResearch(data);
      case "competitor_analysis": return renderCompetitorAnalysis(data);
      case "creative_directions": return renderCreativeDirections(data);
      case "selected_persona":    return renderPersona(data);
      case "image_gen_prompt":    return renderImageGenPrompt(data);
      case "marketing_output":    return renderMarketingOutput(data);
      case "evaluation_output":   return renderEvaluationOutput(data);
      case "channel_adaptation":  return renderChannelAdaptation(data);
      case "brand_consistency":   return renderBrandConsistency(data);
      case "image_generation":    return renderImageGeneration(data);
      default:                    return renderFallback(data);
    }
  } catch {
    return renderFallback(data);
  }
}

// ── Product Profile ───────────────────────────────────────────────────────────
function renderProductProfile(d) {
  const vis = d.visual_attributes || {};
  return `<div class="stage-data">
    ${kv("Product", d.product_name_literal)}
    ${kv("Type", `${d.product_type || ""}${d.subcategory ? " › " + d.subcategory : ""}`)}
    ${kv("Quality", badge(d.quality_tier || ""))}
    ${kv("Summary", d.overall_summary)}
    ${vis.colors?.length ? kv("Colors", tags(vis.colors)) : ""}
    ${vis.materials?.length ? kv("Materials", tags(vis.materials)) : ""}
    ${vis.notable_features?.length ? kv("Features", tags(vis.notable_features)) : ""}
    ${d.use_cases?.length ? kv("Use Cases", list(d.use_cases)) : ""}
    ${d.claims?.length ? kv("Claims", list(d.claims)) : ""}
    ${d.competitor_archetypes?.length ? kv("Competitors", tags(d.competitor_archetypes)) : ""}
  </div>`;
}

// ── Audience Analysis ─────────────────────────────────────────────────────────
function renderAudienceAnalysis(d) {
  const pri = d.primary_audience || {};
  const secondary = d.secondary_audiences || [];
  return `<div class="stage-data">
    ${d.positioning_statement ? kv("Positioning", `<em>${esc(d.positioning_statement)}</em>`) : ""}
    ${pri.demographics ? kv("Primary Audience", pri.demographics) : ""}
    ${pri.psychographics ? kv("Psychographics", pri.psychographics) : ""}
    ${pri.pain_points?.length ? kv("Pain Points", list(pri.pain_points)) : ""}
    ${secondary.length ? kv("Secondary", secondary.map(s => s.demographics || s.name || "").filter(Boolean).join(", ")) : ""}
    ${d.mismatch_flags?.length ? kv("⚠️ Mismatches", `<div style="color:var(--warning)">${list(d.mismatch_flags)}</div>`) : ""}
  </div>`;
}

// ── Trend Research ────────────────────────────────────────────────────────────
function renderTrendResearch(d) {
  const trends = d.trends || [];
  const hooks = d.recommended_hooks || [];
  const aesthetics = d.visual_aesthetic_signals || [];
  return `<div class="stage-data">
    ${d.overall_summary ? `<p style="font-size:13px;margin-bottom:12px;color:var(--text-muted)">${esc(d.overall_summary)}</p>` : ""}
    ${hooks.length ? kv("Top Hooks", list(hooks)) : ""}
    ${aesthetics.length ? kv("Visual Signals", tags(aesthetics)) : ""}
    ${trends.length ? `
      <div style="margin-top:8px">
        ${trends.slice(0, 5).map(t => `
          <div class="concept-card" style="margin-bottom:8px">
            <div style="font-weight:600;font-size:13px;margin-bottom:4px">${esc(t.trend_name || t.name || "")}</div>
            <div style="font-size:12px;color:var(--text-muted)">${esc(t.description || "")}</div>
            ${t.platforms?.length ? `<div style="margin-top:4px">${tags(t.platforms)}</div>` : ""}
            ${t.sources?.length ? `<div style="margin-top:4px">${renderSources(t.sources)}</div>` : ""}
          </div>
        `).join("")}
      </div>
    ` : ""}
  </div>`;
}

// ── Competitor Analysis ───────────────────────────────────────────────────────
function renderCompetitorAnalysis(d) {
  const themes = d.competitor_themes || [];
  const ws = d.whitespace_opportunities || [];
  return `<div class="stage-data">
    ${d.recommended_differentiation ? `<div class="concept-card" style="border-color:var(--accent);margin-bottom:12px"><strong style="color:var(--accent)">Differentiation:</strong> ${esc(d.recommended_differentiation)}</div>` : ""}
    ${themes.length ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin-bottom:6px">Competitor Themes</div>
      ${themes.slice(0, 4).map(t => `
        <div class="concept-card" style="margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <strong style="font-size:13px">${esc(t.theme || "")}</strong>
            ${t.brands_using?.length ? tags(t.brands_using) : ""}
          </div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px">${esc(t.description || t.evidence || "")}</div>
          ${t.sources?.length ? `<div style="margin-top:4px">${renderSources(t.sources)}</div>` : ""}
        </div>
      `).join("")}
    ` : ""}
    ${ws.length ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin:10px 0 6px">Whitespace Opportunities</div>
      ${ws.slice(0, 3).map(w => `
        <div class="concept-card" style="border-color:var(--success);margin-bottom:8px">
          <div style="font-weight:600;font-size:13px;color:var(--success)">${esc(w.angle || "")}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px">${esc(w.rationale || "")}</div>
          ${w.sources?.length ? `<div style="margin-top:4px">${renderSources(w.sources)}</div>` : ""}
        </div>
      `).join("")}
    ` : ""}
  </div>`;
}

// ── Creative Directions ───────────────────────────────────────────────────────
function renderCreativeDirections(d) {
  const dirs = Array.isArray(d) ? d : (d.creative_directions || []);
  const recommended = d.recommended_id;
  return `<div class="stage-data">
    ${dirs.map((c, i) => {
      const isRec = c.id === recommended || i === 0;
      return `
        <div class="concept-card" style="${isRec ? "border-color:var(--accent)" : ""}margin-bottom:10px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
            <strong style="font-size:13px">${esc(c.name || c.concept_name || `Direction ${i+1}`)}</strong>
            ${c.score != null ? `<span class="verdict-badge" style="font-size:11px;padding:2px 8px">${c.score}/10</span>` : ""}
            ${isRec ? `<span class="tag" style="font-size:10px">Recommended</span>` : ""}
          </div>
          <div style="font-size:12px;color:var(--text-muted)">${esc(c.description || c.rationale || "")}</div>
          ${c.tone ? `<div style="margin-top:4px">${tags([c.tone])}</div>` : ""}
        </div>
      `;
    }).join("")}
  </div>`;
}

// ── Persona ───────────────────────────────────────────────────────────────────
function renderPersona(d) {
  const persona = d.persona || d;
  const beliefs = persona.beliefs_values || [];
  const brands = persona.brand_associations || [];
  return `<div class="stage-data">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
      <div style="width:44px;height:44px;border-radius:50%;background:var(--accent-light);border:2px solid var(--accent);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">👤</div>
      <div>
        <div style="font-size:15px;font-weight:700">${esc(persona.name || "")}</div>
        ${persona.age_range ? `<div style="font-size:12px;color:var(--text-muted)">${esc(persona.age_range)}</div>` : ""}
      </div>
    </div>
    ${persona.gender_expression ? kv("Gender", persona.gender_expression) : ""}
    ${persona.ethnicity_description ? kv("Ethnicity", persona.ethnicity_description) : ""}
    ${persona.facial_features ? kv("Facial Features", persona.facial_features) : ""}
    ${persona.body_type ? kv("Body Type", persona.body_type) : ""}
    ${persona.fashion_style ? kv("Style", persona.fashion_style) : ""}
    ${persona.voice_tone ? kv("Voice", persona.voice_tone) : ""}
    ${beliefs.length ? kv("Beliefs", list(beliefs)) : ""}
    ${brands.length ? kv("Brands", tags(brands)) : ""}
    ${d.fit_rationale ? kv("Fit Rationale", d.fit_rationale) : ""}
    ${d.save_new_persona ? `<div class="tag" style="margin-top:6px">New persona saved ✓</div>` : ""}
  </div>`;
}

// ── Image Gen Prompt ──────────────────────────────────────────────────────────
function renderImageGenPrompt(d) {
  const primary = typeof d === "string" ? d : (d.image_gen_prompt || "");
  const variant = typeof d === "string" ? "" : (d.ab_variant_prompt || "");
  return `<div class="stage-data">
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin-bottom:6px">Primary Image Prompt</div>
    <div style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:12px;font-size:12px;line-height:1.6;white-space:pre-wrap;max-height:160px;overflow-y:auto">${esc(primary)}</div>
    ${variant ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin:12px 0 6px">A/B Variant Prompt</div>
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:12px;font-size:12px;line-height:1.6;white-space:pre-wrap;max-height:120px;overflow-y:auto">${esc(variant)}</div>
    ` : ""}
  </div>`;
}

// ── Marketing Output ──────────────────────────────────────────────────────────
function renderMarketingOutput(d) {
  const copy = d.ad_copy_variants || [];
  const platforms = d.recommended_platforms || [];
  const risks = d.legal_compliance_risks || [];
  const recs = d.improvement_recommendations || [];
  return `<div class="stage-data">
    ${d.product_slogan ? `<div class="gen-slogan" style="font-size:16px;margin-bottom:12px">"${esc(d.product_slogan)}"</div>` : ""}
    ${platforms.length ? kv("Top Platforms", platforms.map(p => `<span class="tag">${esc(p.platform || p)}</span>`).join("")) : ""}
    ${copy.length ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin:10px 0 6px">Ad Copy</div>
      ${copy.slice(0, 3).map(c => `
        <div class="concept-card" style="margin-bottom:6px">
          ${c.label ? `<div style="font-size:10px;text-transform:uppercase;color:var(--text-muted);letter-spacing:0.4px;margin-bottom:3px">${esc(c.label)}</div>` : ""}
          <div style="font-size:13px">${esc(c.copy || c)}</div>
        </div>
      `).join("")}
    ` : ""}
    ${d.brand_alignment ? kv("Brand Fit", d.brand_alignment) : ""}
    ${risks.length ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin:10px 0 4px">⚠️ Legal Risks</div>
      ${risks.map(r => `<div style="font-size:12px;padding:3px 0;color:var(--warning)">• [${(r.severity || "").toUpperCase()}] ${esc(r.risk || "")}</div>`).join("")}
    ` : ""}
    ${recs.length ? kv("Improvements", list(recs.map(r => r.recommendation || r).filter(Boolean))) : ""}
  </div>`;
}

// ── Evaluation Output ─────────────────────────────────────────────────────────
function renderEvaluationOutput(d) {
  const dims = d.dimension_scores || d.dimensions || {};
  const risks = d.risks || [];
  const improvements = d.improvements || d.improvement_suggestions || [];
  const score = d.overall_score ?? d.score;
  return `<div class="stage-data">
    ${d.verdict ? `<div class="verdict-badge">${esc(d.verdict)}</div>` : ""}
    ${score != null ? `
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        <div style="font-size:28px;font-weight:700;color:var(--accent)">${score}<span style="font-size:14px;color:var(--text-muted)">/10</span></div>
        <div style="font-size:12px;color:var(--text-muted)">Overall Score</div>
      </div>
    ` : ""}
    ${Object.entries(dims).length ? `
      <div style="margin-bottom:10px">
        ${Object.entries(dims).map(([dim, val]) => {
          const num = typeof val === "object" ? (val.score ?? val.value ?? 0) : val;
          const pct = Math.min(100, Math.round((num / 10) * 100));
          return `
            <div style="margin-bottom:6px">
              <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px">
                <span style="color:var(--text-muted)">${esc(dim.replace(/_/g," "))}</span>
                <span style="font-weight:600">${num}/10</span>
              </div>
              <div class="score-bar-wrap"><div class="score-bar" style="width:${pct}%"></div></div>
            </div>
          `;
        }).join("")}
      </div>
    ` : ""}
    ${risks.length ? kv("Risks", list(risks.map(r => typeof r === "string" ? r : (r.description || r.risk || "")).filter(Boolean))) : ""}
    ${improvements.length ? kv("Improvements", list(improvements.map(i => typeof i === "string" ? i : (i.suggestion || i.text || "")).filter(Boolean))) : ""}
    ${d.competitor_differentiation ? kv("vs Competitors", d.competitor_differentiation) : ""}
  </div>`;
}

// ── Channel Adaptation ────────────────────────────────────────────────────────
function renderChannelAdaptation(d) {
  const copy = d.copy_adaptations || {};
  const fmt = d.format_spec || {};
  const limits = [
    fmt.headline_max_chars ? `Headline ≤${fmt.headline_max_chars} chars` : "",
    fmt.primary_text_max_chars ? `Text ≤${fmt.primary_text_max_chars} chars` : "",
    fmt.recommended_duration_seconds ? `Duration ${fmt.recommended_duration_seconds}s` : "",
  ].filter(Boolean).join(" · ");
  return `<div class="stage-data">
    ${d.platform ? kv("Platform", badge(d.platform)) : ""}
    ${d.aspect_ratio ? kv("Aspect Ratio", badge(d.aspect_ratio)) : ""}
    ${d.adapted_headline ? kv("Headline", d.adapted_headline) : ""}
    ${d.adapted_cta ? kv("CTA", d.adapted_cta) : ""}
    ${copy.hook ? kv("Hook", copy.hook) : ""}
    ${copy.primary_text ? kv("Primary Text", copy.primary_text) : ""}
    ${copy.caption ? kv("Caption", copy.caption) : ""}
    ${d.creative_style_notes ? kv("Style Notes", d.creative_style_notes) : ""}
    ${fmt.format_notes ? kv("Format Notes", fmt.format_notes) : ""}
    ${limits ? kv("Limits", limits) : ""}
  </div>`;
}

// ── Brand Consistency ─────────────────────────────────────────────────────────
function renderBrandConsistency(d) {
  const score = d.consistency_score;
  const pct = score != null ? Math.min(100, Math.round((score / 10) * 100)) : null;
  const notes = d.alignment_notes || d.notes || "";
  const suggestions = d.suggestions || [];
  return `<div class="stage-data">
    ${pct !== null ? `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
        <div style="font-size:28px;font-weight:700;color:${pct >= 70 ? "var(--success)" : "var(--warning)"}">${score}<span style="font-size:14px;color:var(--text-muted)">/10</span></div>
        <div style="flex:1">
          <div class="score-bar-wrap"><div class="score-bar" style="width:${pct}%;background:${pct >= 70 ? "var(--success)" : "var(--warning)"}"></div></div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:3px">Brand Consistency Score</div>
        </div>
      </div>
    ` : ""}
    ${notes ? kv("Notes", notes) : ""}
    ${suggestions.length ? kv("Suggestions", list(suggestions)) : ""}
  </div>`;
}

// ── Image Generation ─────────────────────────────────────────────────────────
function renderImageGeneration(d) {
  const url = d?.url || d?.image_url || "";
  const variantUrl = d?.variant_url || d?.ab_variant_url || "";
  return `<div class="stage-data">
    ${url ? `
      <div style="margin-bottom:10px">
        <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin-bottom:6px">Primary Image</div>
        <img src="${esc(url)}" style="max-width:100%;border-radius:6px;border:1px solid var(--border)" />
      </div>
    ` : `<div class="text-muted" style="font-size:13px">No image generated yet.</div>`}
    ${variantUrl ? `
      <div>
        <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin-bottom:6px">A/B Variant</div>
        <img src="${esc(variantUrl)}" style="max-width:100%;border-radius:6px;border:1px solid var(--border)" />
      </div>
    ` : ""}
  </div>`;
}

// ── Fallback ──────────────────────────────────────────────────────────────────
function renderFallback(d) {
  const str = typeof d === "string" ? d : JSON.stringify(d, null, 2);
  return `<pre style="font-size:11px;white-space:pre-wrap;word-break:break-word;color:var(--text);background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:10px;max-height:300px;overflow-y:auto">${esc(str)}</pre>`;
}

// ── Shared helpers ────────────────────────────────────────────────────────────
function kv(label, value) {
  if (value === undefined || value === null || value === "") return "";
  return `<div class="kv-row"><div class="kv-label">${label}</div><div class="kv-value">${typeof value === "string" && !value.includes("<") ? esc(value) : value}</div></div>`;
}

function tags(arr) {
  return (arr || []).map(t => `<span class="tag">${esc(String(t))}</span>`).join("");
}

function list(arr) {
  return (arr || []).map(i => `<div style="font-size:12px;padding:2px 0;color:var(--text)">• ${esc(String(i))}</div>`).join("");
}

function badge(text) {
  return `<span class="tag">${esc(text)}</span>`;
}

function renderSources(sources) {
  if (!sources?.length) return "";
  return sources.slice(0, 3).map(s => {
    const label = s.label || "source";
    const url = s.url || "";
    return url ? `<a href="${esc(url)}" target="_blank" rel="noopener" class="source-link" style="margin-right:8px">↗ ${esc(label)}</a>` : `<span class="source-link">${esc(label)}</span>`;
  }).join("");
}

function esc(s) {
  return (s || "").toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
