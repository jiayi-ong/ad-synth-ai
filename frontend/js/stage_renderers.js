// Per-stage structured data renderers for the wheel chart expand panel.
// Each renderer returns an HTML string.

export function renderStageData(key, data) {
  if (!data || (typeof data === "object" && data.error)) {
    return `<div class="text-muted" style="font-size:13px">${esc(data?.error || "No data")}</div>`;
  }
  // If the backend couldn't parse the agent's JSON output, it passes the raw string.
  // Show it directly so the user can see what the agent produced.
  if (typeof data === "string") {
    return `<div style="font-size:11px;color:var(--warning);margin-bottom:6px">⚠️ Raw agent output (JSON parse failed)</div>` + renderFallback(data);
  }
  try {
    const rendered = _dispatchRender(key, data);
    // If structured renderer produced only an empty container, show raw JSON instead
    if (rendered.replace(/<div[^>]*><\/div>/g, "").trim() === "") {
      return `<div style="font-size:11px;color:var(--warning);margin-bottom:6px">⚠️ Agent output empty or unexpected structure</div>` + renderFallback(data);
    }
    return rendered;
  } catch {
    return renderFallback(data);
  }
}

function _dispatchRender(key, data) {
  switch (key) {
      case "product_profile":       return renderProductProfile(data);
      case "market_segmentation":   return renderMarketSegmentation(data);
      case "audience_analysis":     return renderAudienceAnalysis(data);
      case "trend_research":        return renderTrendResearch(data);
      case "competitor_analysis":   return renderCompetitorAnalysis(data);
      case "pricing_analysis":      return renderPricingAnalysis(data);
      case "creative_directions":   return renderCreativeDirections(data);
      case "selected_persona":      return renderPersona(data);
      case "image_gen_prompt":      return renderImageGenPrompt(data);
      case "campaign_architecture": return renderCampaignArchitecture(data);
      case "experiment_design":     return renderExperimentDesign(data);
      case "marketing_output":      return renderMarketingOutput(data);
      case "evaluation_output":     return renderEvaluationOutput(data);
      case "channel_adaptation":    return renderChannelAdaptation(data);
      case "brand_consistency":     return renderBrandConsistency(data);
      case "image_generation":      return renderImageGeneration(data);
      default:                      return renderFallback(data);
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
    ${d.compliance_flags ? `
      <div style="margin-top:8px;padding:8px;background:var(--surface2);border:1px solid var(--border);border-radius:6px">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin-bottom:4px">Compliance</div>
        ${d.compliance_flags.regulated_category ? `<div style="font-size:12px"><span class="tag" style="font-size:10px">${esc(d.compliance_flags.regulated_category)}</span> <span style="color:${d.compliance_flags.severity === "high" ? "var(--warning)" : "var(--text-muted)"}">${esc(d.compliance_flags.severity || "")}</span></div>` : ""}
        ${d.compliance_flags.flag_details ? `<div style="font-size:12px;color:var(--text-muted);margin-top:3px">${esc(d.compliance_flags.flag_details)}</div>` : ""}
      </div>
    ` : ""}
    ${renderReadinessScore(d.readiness_score)}
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
    ${d.mismatch_flags?.length ? kv("⚠️ Mismatches", `<div style="color:var(--warning)">${d.mismatch_flags.map(f =>
      typeof f === "string"
        ? `<div style="font-size:12px;margin-bottom:3px">• ${esc(f)}</div>`
        : `<div style="font-size:12px;margin-bottom:5px"><div>• ${esc(f.issue || "")}</div>${f.severity ? `<span class="tag" style="font-size:10px;margin-top:2px">${esc(f.severity)}</span>` : ""}</div>`
    ).join("")}</div>`) : ""}
    ${d.product_understanding_error ? `<div style="color:var(--warning);font-size:12px;margin-top:6px">⚠️ Product understanding mismatch detected</div>` : ""}
    ${renderReadinessScore(d.readiness_score)}
  </div>`;
}

// ── Trend Research ────────────────────────────────────────────────────────────
function renderTrendResearch(d) {
  const trends = d.trends || [];
  const hooks = d.recommended_hooks || [];
  const aesthetics = d.visual_aesthetic_signals || [];
  return `<div class="stage-data">
    ${d.overall_summary ? `<p style="font-size:13px;margin-bottom:12px;color:var(--text-muted)">${esc(d.overall_summary)}</p>` : ""}
    ${renderCharts(d.charts)}
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
    ${renderReadinessScore(d.readiness_score)}
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
          ${c.target_segment ? `<div style="font-size:11px;color:var(--text-muted);margin-top:3px">Segment: ${esc(c.target_segment)}</div>` : ""}
        </div>
      `;
    }).join("")}
    ${renderReadinessScore(d.readiness_score)}
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
    ${renderReadinessScore(d.readiness_score)}
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
    ${d.campaign_fit_assessment ? kv("Campaign Fit", d.campaign_fit_assessment) : ""}
    ${d.experiment_validity_assessment ? kv("Experiment Validity", d.experiment_validity_assessment) : ""}
    ${renderReadinessScore(d.readiness_score)}
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
    ${renderReadinessScore(d.readiness_score)}
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

// ── Market Segmentation ───────────────────────────────────────────────────────
function renderMarketSegmentation(d) {
  const segments = d.segments || [];
  return `<div class="stage-data">
    ${d.recommended_primary_segment ? kv("Primary Segment", badge(d.recommended_primary_segment)) : ""}
    ${d.recommended_secondary_segments?.length ? kv("Secondary Segments", tags(d.recommended_secondary_segments)) : ""}
    ${segments.length ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin:10px 0 6px">Segments</div>
      ${segments.map(s => `
        <div class="concept-card" style="margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">
            <strong style="font-size:13px">${esc(s.name || "")}</strong>
            ${s.attractiveness_score != null ? `<span class="verdict-badge" style="font-size:11px;padding:2px 8px">${s.attractiveness_score}/10</span>` : ""}
          </div>
          <div style="font-size:12px;color:var(--text-muted)">${esc(s.description || "")}</div>
          <div style="display:flex;gap:12px;margin-top:6px;font-size:11px;flex-wrap:wrap">
            ${s.tam_usd_estimate ? `<span><span style="color:var(--text-muted)">TAM</span> <strong>${esc(String(s.tam_usd_estimate))}</strong></span>` : ""}
            ${s.sam_usd_estimate ? `<span><span style="color:var(--text-muted)">SAM</span> <strong>${esc(String(s.sam_usd_estimate))}</strong></span>` : ""}
            ${s.fit_with_product ? `<span><span style="color:var(--text-muted)">Fit</span> <strong>${esc(String(s.fit_with_product))}</strong></span>` : ""}
          </div>
        </div>
      `).join("")}
    ` : ""}
    ${renderCharts(d.charts)}
    ${renderReadinessScore(d.readiness_score)}
  </div>`;
}

// ── Pricing Analysis ──────────────────────────────────────────────────────────
function renderPricingAnalysis(d) {
  const scenarios = d.margin_scenarios || [];
  return `<div class="stage-data">
    ${d.recommended_pricing_model ? kv("Pricing Model", badge(d.recommended_pricing_model)) : ""}
    ${d.recommended_price_point ? kv("Recommended Price", d.recommended_price_point) : ""}
    ${d.break_even_units != null ? kv("Break-even Units", String(d.break_even_units)) : ""}
    ${d.gross_margin_at_recommended_price != null ? kv("Gross Margin", `${Math.round(d.gross_margin_at_recommended_price * 100)}%`) : ""}
    ${d.competitor_pricing_context ? kv("Competitor Context", d.competitor_pricing_context) : ""}
    ${scenarios.length ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin:10px 0 6px">Margin Scenarios</div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead>
            <tr>
              <th style="text-align:left;padding:4px 8px;color:var(--text-muted);font-weight:600;border-bottom:1px solid var(--border)">Price</th>
              <th style="text-align:right;padding:4px 8px;color:var(--text-muted);font-weight:600;border-bottom:1px solid var(--border)">Margin</th>
              <th style="text-align:right;padding:4px 8px;color:var(--text-muted);font-weight:600;border-bottom:1px solid var(--border)">Break-even</th>
            </tr>
          </thead>
          <tbody>
            ${scenarios.map(s => `
              <tr style="border-bottom:1px solid var(--border)">
                <td style="padding:4px 8px">$${esc(String(s.price_usd ?? ""))}</td>
                <td style="text-align:right;padding:4px 8px">${s.gross_margin_pct != null ? Math.round(s.gross_margin_pct * 100) + "%" : ""}</td>
                <td style="text-align:right;padding:4px 8px">${s.break_even_units ?? ""}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    ` : ""}
    ${d.pricing_risks?.length ? kv("Pricing Risks", list(d.pricing_risks)) : ""}
    ${renderCharts(d.charts)}
    ${renderReadinessScore(d.readiness_score)}
  </div>`;
}

// ── Campaign Architecture ─────────────────────────────────────────────────────
function renderCampaignArchitecture(d) {
  const phases = d.campaign_phases || [];
  const budgetAlloc = d.budget_allocation_pct || {};
  const metrics = d.success_metrics || [];
  return `<div class="stage-data">
    ${d.campaign_objective ? kv("Objective", d.campaign_objective) : ""}
    ${d.timeline_weeks_total ? kv("Duration", `${d.timeline_weeks_total} weeks`) : ""}
    ${phases.length ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin:10px 0 6px">Phases</div>
      ${phases.map((p, i) => `
        <div class="concept-card" style="margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">
            <strong style="font-size:13px">${i + 1}. ${esc(p.name || "")}</strong>
            ${p.duration_weeks ? `<span class="tag" style="font-size:10px">${p.duration_weeks}w</span>` : ""}
          </div>
          ${p.goal ? `<div style="font-size:12px;color:var(--text-muted)">${esc(p.goal)}</div>` : ""}
          ${p.primary_channel ? `<div style="margin-top:4px">${tags([p.primary_channel])}</div>` : ""}
          ${p.key_message ? `<div style="font-size:12px;margin-top:4px;font-style:italic">"${esc(p.key_message)}"</div>` : ""}
        </div>
      `).join("")}
    ` : ""}
    ${Object.keys(budgetAlloc).length ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin:10px 0 6px">Budget Allocation</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
        ${Object.entries(budgetAlloc).map(([k, v]) => `
          <div style="font-size:12px"><span style="color:var(--text-muted)">${esc(k)}</span> <strong>${v}%</strong></div>
        `).join("")}
      </div>
    ` : ""}
    ${metrics.length ? `
      <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin:10px 0 6px">Success Metrics</div>
      ${metrics.slice(0, 4).map(m => `
        <div style="font-size:12px;padding:3px 0">
          <strong>${esc(m.metric || "")}</strong>
          ${m.target ? ` → ${esc(String(m.target))}` : ""}
          ${m.measurement_method ? `<span style="color:var(--text-muted)"> (${esc(m.measurement_method)})</span>` : ""}
        </div>
      `).join("")}
    ` : ""}
    ${renderReadinessScore(d.readiness_score)}
  </div>`;
}

// ── Experiment Design ─────────────────────────────────────────────────────────
function renderExperimentDesign(d) {
  const experiments = d.experiments || [];
  return `<div class="stage-data">
    ${experiments.map((e, i) => `
      <div class="concept-card" style="margin-bottom:10px">
        <div style="font-size:13px;font-weight:700;margin-bottom:4px">${esc(e.name || `Experiment ${i + 1}`)}</div>
        ${e.hypothesis ? `<div style="font-size:12px;color:var(--text-muted);margin-bottom:6px"><em>${esc(e.hypothesis)}</em></div>` : ""}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:12px">
          ${e.primary_metric ? `<div><span style="color:var(--text-muted)">Metric</span> <strong>${esc(e.primary_metric)}</strong></div>` : ""}
          ${e.sample_size_per_arm != null ? `<div><span style="color:var(--text-muted)">Sample/arm</span> <strong>${Number(e.sample_size_per_arm).toLocaleString()}</strong></div>` : ""}
          ${e.statistical_power != null ? `<div><span style="color:var(--text-muted)">Power</span> <strong>${Math.round(e.statistical_power * 100)}%</strong></div>` : ""}
          ${e.significance_level != null ? `<div><span style="color:var(--text-muted)">Significance</span> <strong>α=${e.significance_level}</strong></div>` : ""}
          ${e.minimum_detectable_effect_pct != null ? `<div><span style="color:var(--text-muted)">MDE</span> <strong>${e.minimum_detectable_effect_pct}%</strong></div>` : ""}
          ${e.estimated_duration_days != null ? `<div><span style="color:var(--text-muted)">Duration</span> <strong>${e.estimated_duration_days}d</strong></div>` : ""}
        </div>
        ${e.control && e.variant ? `
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">
            <div style="background:var(--surface2);border-radius:4px;padding:6px;font-size:11px"><span style="color:var(--text-muted)">Control</span><br/>${esc(e.control)}</div>
            <div style="background:var(--surface2);border-radius:4px;padding:6px;font-size:11px"><span style="color:var(--text-muted)">Variant</span><br/>${esc(e.variant)}</div>
          </div>
        ` : ""}
      </div>
    `).join("")}
    ${d.prioritization_rationale ? kv("Prioritization", d.prioritization_rationale) : ""}
    ${renderCharts(d.charts)}
    ${renderReadinessScore(d.readiness_score)}
  </div>`;
}

// ── Fallback ──────────────────────────────────────────────────────────────────
function renderFallback(d) {
  const str = typeof d === "string" ? d : JSON.stringify(d, null, 2);
  return `<pre style="font-size:11px;white-space:pre-wrap;word-break:break-word;color:var(--text);background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:10px;max-height:300px;overflow-y:auto">${esc(str)}</pre>`;
}

// ── Shared helpers ────────────────────────────────────────────────────────────
function renderReadinessScore(rs) {
  if (!rs) return "";
  return `
    <div style="margin-top:12px;padding:10px;background:var(--surface2);border:1px solid var(--border);border-radius:6px">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);margin-bottom:8px">Readiness</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
        ${rs.completeness != null ? `<div style="font-size:12px"><span style="color:var(--text-muted)">Completeness</span> <strong>${Math.min(100, Math.round(rs.completeness * 100))}%</strong></div>` : ""}
        ${rs.source_grounding != null ? `<div style="font-size:12px"><span style="color:var(--text-muted)">Grounding</span> <strong>${Math.min(100, Math.round(rs.source_grounding * 100))}%</strong></div>` : ""}
        ${rs.confidence != null ? `<div style="font-size:12px"><span style="color:var(--text-muted)">Confidence</span> <strong>${Math.min(100, Math.round(rs.confidence * 100))}%</strong></div>` : ""}
        ${rs.risk_level ? `<div style="font-size:12px"><span style="color:var(--text-muted)">Risk</span> <strong style="color:${rs.risk_level === "low" ? "var(--success)" : rs.risk_level === "high" ? "var(--warning)" : "var(--text)"}">${esc(rs.risk_level)}</strong></div>` : ""}
      </div>
    </div>
  `;
}

function renderCharts(charts) {
  if (!charts?.length) return "";
  return charts.map(c => `
    <div style="margin-top:12px">
      ${c.title ? `<div style="font-size:12px;font-weight:700;color:var(--text-muted);margin-bottom:4px">${esc(c.title)}</div>` : ""}
      ${c.description ? `<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">${esc(c.description)}</div>` : ""}
      ${c.image_base64 ? `<img src="data:image/png;base64,${c.image_base64}" style="max-width:100%;border-radius:6px;border:1px solid var(--border)" />` : ""}
    </div>
  `).join("");
}

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
