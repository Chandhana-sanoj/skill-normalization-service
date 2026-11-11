// ── Token storage (separate from org-user localStorage key) ──────────────────
const SA_TOKEN_KEY = "sa_token";

export function getToken() {
  return sessionStorage.getItem(SA_TOKEN_KEY);
}

export function setToken(token) {
  sessionStorage.setItem(SA_TOKEN_KEY, token);
}

export function clearToken() {
  sessionStorage.removeItem(SA_TOKEN_KEY);
}

// ── Core request helper ───────────────────────────────────────────────────────
export async function apiRequest(path, { method = "GET", body = null, token = null } = {}) {
  const headers = { "Content-Type": "application/json" };
  const tok = token ?? getToken();
  if (tok) headers["Authorization"] = `Bearer ${tok}`;

  const res = await fetch(path, { method, headers, body });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json?.detail || json?.message || detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function login(username, password) {
  const data = await apiRequest("/api/v1/super-admin/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(data.access_token);
  return data;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export async function fetchDashboard() {
  return apiRequest("/api/v1/super-admin/dashboard");
}

// ── Organizations ─────────────────────────────────────────────────────────────
export async function fetchOrganizations() {
  return apiRequest("/api/v1/super-admin/organizations");
}

export async function updateOrgStatus(id, is_active) {
  return apiRequest(`/api/v1/super-admin/organizations/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ is_active }),
  });
}

export async function deleteOrganization(id) {
  return apiRequest(`/api/v1/super-admin/organizations/${id}`, { method: "DELETE" });
}

// ── Users ─────────────────────────────────────────────────────────────────────
export async function fetchUsers() {
  return apiRequest("/api/v1/super-admin/users");
}

export async function updateUserStatus(id, is_active) {
  return apiRequest(`/api/v1/super-admin/users/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ is_active }),
  });
}

// ── Canonical Skills ──────────────────────────────────────────────────────────
export async function fetchSkills({ search = "", page = 1, limit = 25 } = {}) {
  const p = new URLSearchParams();
  if (search) p.set("search", search);
  p.set("page", String(page));
  p.set("limit", String(limit));
  return apiRequest(`/api/v1/super-admin/skills?${p}`);
}

export async function fetchSkillById(skillId) {
  return apiRequest(`/api/v1/super-admin/skills/${skillId}`);
}

export async function fetchSkillAliases(skillId) {
  return apiRequest(`/api/v1/super-admin/skills/${skillId}/aliases`);
}

export async function createSkill(payload) {
  return apiRequest("/api/v1/super-admin/skills", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSkill(id, payload) {
  return apiRequest(`/api/v1/super-admin/skills/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function addSkillAlias(skillId, alias) {
  return apiRequest(`/api/v1/super-admin/skills/${skillId}/aliases`, {
    method: "POST",
    body: JSON.stringify({ alias }),
  });
}

export async function deleteSkillAlias(skillId, aliasId) {
  return apiRequest(`/api/v1/super-admin/skills/${skillId}/aliases/${aliasId}`, {
    method: "DELETE",
  });
}

// ── Normalization History ─────────────────────────────────────────────────────
export async function fetchHistory({ search = "", status = "", page = 1, limit = 25 } = {}) {
  const p = new URLSearchParams();
  if (search) p.set("search", search);
  if (status) p.set("status", status);
  p.set("page", String(page));
  p.set("limit", String(limit));
  return apiRequest(`/api/v1/super-admin/normalization-history?${p}`);
}

// ── Unresolved Skills ─────────────────────────────────────────────────────────
export async function fetchUnresolved({ search = "", page = 1, limit = 25 } = {}) {
  const p = new URLSearchParams();
  if (search) p.set("search", search);
  p.set("page", String(page));
  p.set("limit", String(limit));
  return apiRequest(`/api/v1/super-admin/unresolved-skills?${p}`);
}

// ── Org Skill Review ──────────────────────────────────────────────────────────
export async function fetchOrgSkillReview({ search = "", status = "", page = 1, limit = 25 } = {}) {
  const p = new URLSearchParams();
  if (search) p.set("search", search);
  if (status) p.set("status", status);
  p.set("page", String(page));
  p.set("limit", String(limit));
  return apiRequest(`/api/v1/super-admin/org-skill-review?${p}`);
}

export async function approveOrgSkill(skillId, payload = {}) {
  return apiRequest(`/api/v1/super-admin/org-skill-review/${skillId}/approve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function rejectOrgSkill(skillId) {
  return apiRequest(`/api/v1/super-admin/org-skill-review/${skillId}/reject`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}
