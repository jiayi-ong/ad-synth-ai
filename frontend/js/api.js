const BASE = "";  // same origin

export function getToken() {
  return localStorage.getItem("token");
}

export function setToken(token) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
  localStorage.removeItem("user_email");
}

async function request(method, path, body = null, isForm = false) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body && !isForm) headers["Content-Type"] = "application/json";

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: isForm ? body : (body ? JSON.stringify(body) : undefined),
  });

  if (res.status === 401) {
    clearToken();
    window.location.hash = "#login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  post: (path, body) => request("POST", path, body),
  postForm: (path, form) => request("POST", path, form, true),
  get: (path) => request("GET", path),
  patch: (path, body) => request("PATCH", path, body),
  delete: (path) => request("DELETE", path),

  // Auth
  register: (email, password) => request("POST", "/auth/register", { email, password }),
  login: async (email, password) => {
    const form = new URLSearchParams({ username: email, password });
    const res = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail);
    }
    return res.json();
  },

  // Campaigns
  getCampaigns: () => request("GET", "/campaigns"),
  createCampaign: (data) => request("POST", "/campaigns", data),
  updateCampaign: (id, data) => request("PATCH", `/campaigns/${id}`, data),
  deleteCampaign: (id) => request("DELETE", `/campaigns/${id}`),

  // Products (all across campaigns, or scoped to one campaign)
  getAllProducts: () => request("GET", "/products"),
  getProducts: (cid) => request("GET", `/campaigns/${cid}/products`),
  createProduct: (cid, data) => request("POST", `/campaigns/${cid}/products`, data),
  updateProduct: (cid, pid, data) => request("PATCH", `/campaigns/${cid}/products/${pid}`, data),
  deleteProduct: (cid, pid) => request("DELETE", `/campaigns/${cid}/products/${pid}`),
  uploadImage: (cid, pid, file) => {
    const form = new FormData();
    form.append("file", file);
    return request("POST", `/campaigns/${cid}/products/${pid}/image`, form, true);
  },

  // Personas (all across campaigns, or scoped to one campaign)
  getAllPersonas: () => request("GET", "/personas"),
  getPersonas: (cid) => request("GET", `/campaigns/${cid}/personas`),
  createPersona: (cid, data) => request("POST", `/campaigns/${cid}/personas`, data),
  updatePersona: (cid, pid, data) => request("PATCH", `/campaigns/${cid}/personas/${pid}`, data),
  deletePersona: (cid, pid) => request("DELETE", `/campaigns/${cid}/personas/${pid}`),

  // Advertisements
  getAdvertisements: (cid) => request("GET", `/campaigns/${cid}/advertisements`),
  getAdvertisement: (cid, aid) => request("GET", `/campaigns/${cid}/advertisements/${aid}`),
  deleteAdvertisement: (cid, aid) => request("DELETE", `/campaigns/${cid}/advertisements/${aid}`),
  cancelGeneration: (adId) => request("POST", `/generate/${adId}/cancel`, {}),
  rerunStage: (adId, stageKey, extraInput, rerunDownstream) =>
    request("POST", `/generate/${adId}/rerun-stage`, { stage_key: stageKey, extra_input: extraInput || null, rerun_downstream: rerunDownstream }),
  retryImage: (adId) => request("POST", `/generate/${adId}/retry-image`, {}),

  // Brands
  getBrands: () => request("GET", "/brands"),
  getBrand: (bid) => request("GET", `/brands/${bid}`),
  createBrand: (data) => request("POST", "/brands", data),
  updateBrand: (bid, data) => request("PATCH", `/brands/${bid}`, data),
  deleteBrand: (bid) => request("DELETE", `/brands/${bid}`),

  getBrandProducts: (bid) => request("GET", `/brands/${bid}/products`),
  createBrandProduct: (bid, data) => request("POST", `/brands/${bid}/products`, data),
  updateBrandProduct: (bid, pid, data) => request("PATCH", `/brands/${bid}/products/${pid}`, data),
  deleteBrandProduct: (bid, pid) => request("DELETE", `/brands/${bid}/products/${pid}`),
  uploadBrandProductImage: (bid, pid, file) => {
    const form = new FormData();
    form.append("file", file);
    return request("POST", `/brands/${bid}/products/${pid}/image`, form, true);
  },

  getBrandPersonas: (bid) => request("GET", `/brands/${bid}/personas`),
  createBrandPersona: (bid, data) => request("POST", `/brands/${bid}/personas`, data),
  deleteBrandPersona: (bid, pid) => request("DELETE", `/brands/${bid}/personas/${pid}`),

  // Research
  startResearch: (data) => request("POST", "/research", data),
  getResearchHistory: () => request("GET", "/research"),
  getResearchResult: (id) => request("GET", `/research/${id}`),

  // Evaluate
  evaluate: (data) => request("POST", "/evaluate", data),
};
