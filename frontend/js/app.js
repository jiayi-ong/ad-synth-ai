import { bindAuth, logout, renderAuth } from "./auth.js";
import { bindCampaigns, renderCampaigns } from "./campaigns.js";
import { bindProject, renderProject } from "./project.js";
import { bindGenerate, renderGenerate } from "./generate.js";
import { getToken } from "./api.js";

const app = document.getElementById("app");
const nav = document.getElementById("main-nav");

function setNav(loggedIn) {
  if (!loggedIn) {
    nav.style.display = "none";
    return;
  }
  nav.style.display = "flex";
  const email = localStorage.getItem("user_email") || "";
  document.getElementById("nav-user").textContent = email;
}

async function route() {
  const hash = window.location.hash || "#login";
  const token = getToken();

  // Guard: redirect to login if not authenticated
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

window.addEventListener("hashchange", route);
route();
