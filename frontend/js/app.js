import { bindAuth, logout, renderAuth } from "./auth.js";
import { bindCampaigns, renderCampaigns } from "./campaigns.js";
import { bindProject, renderProject } from "./project.js";
import { bindGenerate, renderGenerate } from "./generate.js";
import { bindBrands, renderBrands } from "./brands.js";
import { bindResearch, renderResearch } from "./research.js";
import { bindLibrary, renderLibrary } from "./library.js";
import { getToken } from "./api.js";

const app = document.getElementById("app");
const nav = document.getElementById("main-nav");

// ── Expert mode toggle ────────────────────────────────────────────────────────

function initExpertMode() {
  const stored = localStorage.getItem("ui_mode");
  if (stored === "expert") document.body.classList.add("expert-mode");
  updateModeToggleLabel();
}

function updateModeToggleLabel() {
  const btn = document.getElementById("mode-toggle");
  if (!btn) return;
  const expert = document.body.classList.contains("expert-mode");
  btn.textContent = expert ? "Simple Mode" : "Expert Mode";
}

window.toggleMode = function () {
  document.body.classList.toggle("expert-mode");
  const expert = document.body.classList.contains("expert-mode");
  localStorage.setItem("ui_mode", expert ? "expert" : "simple");
  updateModeToggleLabel();
};

// ── Nav ───────────────────────────────────────────────────────────────────────

function setNav(loggedIn) {
  if (!loggedIn) {
    nav.style.display = "none";
    return;
  }
  nav.style.display = "flex";
  const email = localStorage.getItem("user_email") || "";
  document.getElementById("nav-user").textContent = email;
}

// ── Router ────────────────────────────────────────────────────────────────────

async function route() {
  const hash = window.location.hash || "#login";
  const token = getToken();

  const publicRoutes = ["#login", "#register"];
  if (!token && !publicRoutes.includes(hash.split("/")[0])) {
    window.location.hash = "#login";
    return;
  }

  setNav(!!token);

  if (hash === "#login") {
    setNav(false);
    app.innerHTML = renderAuth("login");
    bindAuth("login");
  } else if (hash === "#register") {
    setNav(false);
    app.innerHTML = renderAuth("register");
    bindAuth("register");
  } else if (hash === "#campaigns") {
    app.innerHTML = await renderCampaigns();
    bindCampaigns();
  } else if (hash === "#brands") {
    app.innerHTML = await renderBrands();
    bindBrands();
  } else if (hash.startsWith("#brands/")) {
    const brandId = hash.split("/")[1];
    app.innerHTML = await renderBrands(brandId);
    bindBrands(brandId);
  } else if (hash === "#research") {
    app.innerHTML = renderResearch();
    bindResearch();
  } else if (hash === "#library") {
    app.innerHTML = await renderLibrary();
    bindLibrary();
  } else if (hash.startsWith("#project/")) {
    const campaignId = hash.split("/")[1];
    app.innerHTML = await renderProject(campaignId);
    bindProject(campaignId);
  } else if (hash.startsWith("#generate/")) {
    const parts = hash.split("/");
    const campaignId = parts[1];
    const existingAdId = parts[2] || null;
    app.innerHTML = await renderGenerate(campaignId, existingAdId);
    bindGenerate(campaignId);
  } else {
    window.location.hash = token ? "#campaigns" : "#login";
  }
}

document.getElementById("nav-logout")?.addEventListener("click", logout);
document.getElementById("mode-toggle")?.addEventListener("click", window.toggleMode);

initExpertMode();
window.addEventListener("hashchange", route);
route();
