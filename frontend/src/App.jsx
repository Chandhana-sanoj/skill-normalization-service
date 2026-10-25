// src/App.jsx

import { useState, useEffect, useCallback } from "react";
import "./App.css";

// Backend URL can be overridden in .env with VITE_API_BASE_URL.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function apiRequest(path, { token, ...options } = {}) {
  const headers = { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error(`Cannot reach the backend at ${API_BASE_URL}. Check that FastAPI is running and CORS allows the frontend origin.`);
  }
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof data === "object" && data !== null ? (data.detail || data.message) : data;
    throw new Error(detail ? (typeof detail === "string" ? detail : JSON.stringify(detail)) : `Request failed (${response.status}).`);
  }
  return data;
}

function makeSession(user, token) {
  const rawRole = String(user.role || "user").toLowerCase();
  return {
    token,
    username: user.username || user.email || user.sub || "User",
    role: ["org_admin", "admin", "organization_admin"].includes(rawRole) ? "Admin" : "User",
    orgName: user.organization_name || user.org_name || "Your organization",
    orgId: user.organization_id || "",
  };
}

const NAV_ITEMS = [
  { id: "catalog",    label: "Main Catalog",         adminOnly: false },
  { id: "org-skills", label: "Organization Skills",  adminOnly: false },
  { id: "unresolved", label: "Unresolved Skills",    adminOnly: true  },
  { id: "normalize",  label: "Normalize Skill",      adminOnly: false }, // NEW
  { id: "output",     label: "Normalization Output", adminOnly: false },
];

const PAGE_SIZE = 25;

// ══════════════════════════════════════════════════════════════════════════════
// SHARED COMPONENTS
// ══════════════════════════════════════════════════════════════════════════════

function Paginator({ page, total, pageSize, onPrev, onNext }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end   = Math.min(page * pageSize, total);
  return (
    <div className="paginator">
      <span className="paginator-info">{total === 0 ? "0 results" : `${start}–${end} of ${total.toLocaleString()}`}</span>
      <div className="paginator-controls">
        <button className="paginator-btn" onClick={onPrev} disabled={page <= 1} aria-label="Previous page">← Prev</button>
        <span className="paginator-page">Page {page} of {totalPages}</span>
        <button className="paginator-btn" onClick={onNext} disabled={page >= totalPages} aria-label="Next page">Next →</button>
      </div>
    </div>
  );
}

function SearchBar({ id, value, onChange, placeholder, label }) {
  return (
    <div className="toolbar-search">
      <svg className="toolbar-search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input id={id} type="search" className="toolbar-input" placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} aria-label={label} />
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// CATALOG PAGE
// ══════════════════════════════════════════════════════════════════════════════
async function fetchCatalog({ search, category, page, token }) {
  const params = new URLSearchParams();
  if (search)   params.set("q", search);
  if (category) params.set("category", category);
  params.set("page",  String(page));
  params.set("limit", String(PAGE_SIZE));
  return apiRequest(`/api/v1/catalog?${params.toString()}`, { token });
}

function CatalogPage({ session }) {
  const [search, setSearch]     = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage]         = useState(1);
  const [items, setItems]       = useState([]);
  const [total, setTotal]       = useState(0);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [debouncedSearch, setDebouncedSearch] = useState(search);

  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 400); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(1); }, [debouncedSearch, category]);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await fetchCatalog({ search: debouncedSearch, category, page, token: session.token });
      setItems(data.items ?? []); setTotal(data.total ?? 0);
      if (categories.length === 0 && data.categories) setCategories(data.categories);
    } catch (err) { setError(err.message || "An unexpected error occurred."); setItems([]); setTotal(0); }
    finally { setLoading(false); }
  }, [debouncedSearch, category, page]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page">
      <div className="page-header"><div><h1 className="page-title">Main Catalog</h1><p className="page-subtitle">Shared catalogue of standardised skills.&ensp;{!loading && !error && <strong>{total.toLocaleString()} skills</strong>}</p></div></div>
      <div className="toolbar">
        <SearchBar id="catalog-search" value={search} onChange={setSearch} placeholder="Search skills…" label="Search the skill catalog" />
        <div className="toolbar-filter">
          <label htmlFor="catalog-category" className="sr-only">Filter by category</label>
          <select id="catalog-category" className="toolbar-select" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            {categories.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
          </select>
        </div>
      </div>
      {loading && <div className="state-loading" aria-live="polite"><span className="spinner" aria-hidden="true" />Loading skills…</div>}
      {!loading && error && <div className="state-error" role="alert"><strong>Could not load catalog.</strong><p>{error}</p><button className="retry-btn" onClick={load}>Try again</button></div>}
      {!loading && !error && (
        <>
          {items.length === 0
            ? <div className="table-empty"><p>No skills matched your search.</p></div>
            : (
              <div className="table-wrapper">
                <table className="data-table" aria-label="Skill catalog">
                  <thead><tr><th scope="col">Normalized Skill</th><th scope="col">Category</th><th scope="col">Description</th></tr></thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.id}>
                        <td className="cell-skill">{item.normalizedSkill}</td>
                        <td><span className="category-tag">{item.category}</span></td>
                        <td className="cell-description">{item.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
          <Paginator page={page} total={total} pageSize={PAGE_SIZE} onPrev={() => setPage((p) => p - 1)} onNext={() => setPage((p) => p + 1)} />
        </>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// ORGANIZATION SKILLS PAGE
// ══════════════════════════════════════════════════════════════════════════════
async function fetchOrgSkills({ search, page, token }) {
  const params = new URLSearchParams();
  if (search) params.set("q", search);
  params.set("page",  String(page));
  params.set("limit", String(PAGE_SIZE));
  return apiRequest(`/api/v1/organizations/me/skills?${params.toString()}`, { token });
}

async function fetchCategories(token) {
  try {
    const data = await apiRequest("/api/v1/organizations/me/categories", { token });
    return data.categories ?? [];
  } catch {
    return [];
  }
}

async function saveOrgSkill({ skill, token }) {
  const body = {
    raw_skill:        skill.rawSkill,
    normalized_skill: skill.normalizedSkill,
    category:         skill.category  || null,
    description:      skill.description || null,
  };
  if (skill.id) {
    return apiRequest(`/api/v1/organizations/me/skills/${skill.id}`, {
      method: "PUT",
      token,
      body: JSON.stringify(body),
    });
  }
  return apiRequest("/api/v1/organizations/me/skills", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

async function deleteOrgSkill({ id, token }) {
  return apiRequest(`/api/v1/organizations/me/skills/${id}`, { method: "DELETE", token });
}

async function promoteUnresolved({ unresolvedId, skill, token }) {
  return apiRequest(
    `/api/v1/organizations/me/unresolved/${unresolvedId}/promote`,
    {
      method: "POST",
      token,
      body: JSON.stringify({
        raw_skill:        skill.rawSkill,
        normalized_skill: skill.normalizedSkill,
        category:         skill.category     || null,
        description:      skill.description  || null,
      }),
    }
  );
}

const BLANK_ORG_SKILL = { rawSkill: "", normalizedSkill: "", category: "", description: "" };

// ── Shared skill form modal (Add Skill / Edit Skill) ──────────────────────────
function SkillFormModal({ initial, onSave, onClose, saving, saveError, token }) {
  const [form, setForm] = useState(() => {
    if (!initial) return BLANK_ORG_SKILL;
    // Map API response fields → form fields (description may come from either field name)
    return {
      rawSkill:        initial.rawSkill        ?? "",
      normalizedSkill: initial.normalizedSkill ?? "",
      category:        initial.category        ?? "",
      description:     initial.description     ?? initial.notes ?? "",
    };
  });
  const [categories, setCategories] = useState([]);
  const isEdit = Boolean(initial?.id);

  useEffect(() => {
    fetchCategories(token).then(setCategories);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleChange(e) { setForm((prev) => ({ ...prev, [e.target.name]: e.target.value })); }
  function handleSubmit(e) {
    e.preventDefault();
    onSave(isEdit ? { ...form, id: initial.id } : form);
  }
  function handleBackdropClick(e) { if (e.target === e.currentTarget) onClose(); }

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick} role="dialog" aria-modal="true" aria-label={isEdit ? "Edit skill" : "Add skill"}>
      <div className="modal-card">
        <div className="modal-header">
          <h2 className="modal-title">{isEdit ? "Edit Skill" : "Add Skill"}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {saveError && <div className="modal-error" role="alert"><strong>Could not save.</strong> {saveError}</div>}
        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="rawSkill">Raw Skill <span className="required">*</span></label>
            <input id="rawSkill" name="rawSkill" type="text" value={form.rawSkill} onChange={handleChange} placeholder="e.g. react.js" required />
            <span className="field-hint">The skill name as your organisation uses it.</span>
          </div>
          <div className="form-field">
            <label htmlFor="normalizedSkill">Normalized Skill <span className="required">*</span></label>
            <input id="normalizedSkill" name="normalizedSkill" type="text" value={form.normalizedSkill} onChange={handleChange} placeholder="e.g. React" required />
            <span className="field-hint">The canonical standardised skill name.</span>
          </div>
          <div className="form-field">
            <label htmlFor="category">Category <span className="required">*</span></label>
            <select id="category" name="category" value={form.category} onChange={handleChange} required>
              <option value="">— select a category —</option>
              {categories.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
            </select>
            <span className="field-hint">Choose from the canonical catalogue categories.</span>
          </div>
          <div className="form-field">
            <label htmlFor="description">Description</label>
            <textarea id="description" name="description" rows={3} value={form.description} onChange={handleChange} placeholder="Optional description…" />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Saving…" : isEdit ? "Save changes" : "Add skill"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function OrgSkillsPage({ session }) {
  const isAdmin = session.role === "Admin";
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 400); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(1); }, [debouncedSearch]);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { const data = await fetchOrgSkills({ search: debouncedSearch, page, token: session.token }); setItems(data.items ?? []); setTotal(data.total ?? 0); }
    catch (err) { setError(err.message || "An unexpected error occurred."); setItems([]); setTotal(0); }
    finally { setLoading(false); }
  }, [session.orgId, debouncedSearch, page]);

  useEffect(() => { load(); }, [load]);

  function openAdd() { setEditTarget(null); setSaveError(null); setDeleteError(null); setModalOpen(true); }
  function openEdit(item) { setEditTarget(item); setSaveError(null); setDeleteError(null); setModalOpen(true); }
  function closeModal() { setModalOpen(false); setEditTarget(null); setSaveError(null); }

  async function handleSave(formData) {
    setSaving(true); setSaveError(null);
    try { await saveOrgSkill({ skill: formData, token: session.token }); closeModal(); load(); }
    catch (err) { setSaveError(err.message || "An unexpected error occurred."); }
    finally { setSaving(false); }
  }

  async function handleDelete(item) {
    setDeleteError(null);
    if (!window.confirm(`Delete "${item.rawSkill || item.normalizedSkill}" from your organisation skills?`)) return;
    try { await deleteOrgSkill({ id: item.id, token: session.token }); load(); }
    catch (err) { setDeleteError(err.message || "Delete failed."); }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div><h1 className="page-title">Organization Skills</h1><p className="page-subtitle">Skills for <strong>{session.orgName}</strong> ({session.orgId}).&ensp;{!loading && !error && <span>{total.toLocaleString()} {total === 1 ? "skill" : "skills"}</span>}</p></div>
        {isAdmin && <button id="add-org-skill-btn" className="btn-primary" onClick={openAdd}>+ Add Skill</button>}
      </div>
      <div className="toolbar"><SearchBar id="org-skills-search" value={search} onChange={setSearch} placeholder="Search organisation skills…" label="Search organisation skills" /></div>
      {deleteError && <div className="state-error" role="alert"><strong>Delete failed.</strong><p>{deleteError}</p></div>}
      {loading && <div className="state-loading" aria-live="polite"><span className="spinner" aria-hidden="true" />Loading skills…</div>}
      {!loading && error && <div className="state-error" role="alert"><strong>Could not load organisation skills.</strong><p>{error}</p><button className="retry-btn" onClick={load}>Try again</button></div>}
      {!loading && !error && (
        <>
          {items.length === 0
            ? <div className="table-empty"><p>No skills found. {isAdmin ? 'Use the "Add Skill" button to get started.' : "Contact your admin to add skills."}</p></div>
            : (
              <div className="table-wrapper">
                <table className="data-table" aria-label="Organisation skills">
                  <thead><tr><th scope="col">Raw Skill</th><th scope="col">Normalized Skill</th><th scope="col">Category</th><th scope="col">Description</th>{isAdmin && <th scope="col"><span className="sr-only">Actions</span></th>}</tr></thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.id}>
                        <td className="cell-raw">{item.rawSkill}</td>
                        <td className="cell-skill">{item.normalizedSkill || <span className="cell-empty">—</span>}</td>
                        <td>{item.category ? <span className="category-tag">{item.category}</span> : <span className="cell-empty">—</span>}</td>
                        <td className="cell-description">{item.description || <span className="cell-empty">—</span>}</td>
                        {isAdmin && (
                          <td className="cell-actions">
                            <button className="action-btn" onClick={() => openEdit(item)} aria-label={`Edit ${item.rawSkill}`}>Edit</button>
                            <button className="action-btn action-btn--delete" onClick={() => handleDelete(item)} aria-label={`Delete ${item.rawSkill}`}>Delete</button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
          <Paginator page={page} total={total} pageSize={PAGE_SIZE} onPrev={() => setPage((p) => p - 1)} onNext={() => setPage((p) => p + 1)} />
        </>
      )}
      {modalOpen && <SkillFormModal initial={editTarget} onSave={handleSave} onClose={closeModal} saving={saving} saveError={saveError} token={session.token} />}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// UNRESOLVED SKILLS PAGE
// ══════════════════════════════════════════════════════════════════════════════
async function fetchUnresolvedSkills({ search, page, token }) {
  const params = new URLSearchParams();
  if (search) params.set("q", search);
  params.set("page",  String(page));
  params.set("limit", String(PAGE_SIZE));
  // Organization is resolved server-side from the Bearer token.
  return apiRequest(`/api/v1/organizations/me/unresolved?${params.toString()}`, { token });
}

async function resolveSkill({ resolution, token }) {
  return apiRequest(
    `/api/v1/organizations/me/unresolved/${resolution.id}/resolve`,
    {
      method: "POST",
      token,
      body: JSON.stringify({
        normalized_skill: resolution.normalizedSkill || null,
        category: resolution.category || null,
        notes: resolution.notes || null,
      }),
    }
  );
}

async function updateUnresolvedSkill({ id, input, token }) {
  return apiRequest(
    `/api/v1/organizations/me/unresolved/${id}`,
    {
      method: "PUT",
      token,
      body: JSON.stringify({ input }),
    }
  );
}

async function deleteUnresolvedSkill({ id, token }) {
  return apiRequest(
    `/api/v1/organizations/me/unresolved/${id}`,
    { method: "DELETE", token }
  );
}

function ConfidencePill({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  let level = "low";
  if (pct >= 85) level = "high";
  else if (pct >= 60) level = "mid";
  return <span className={`confidence-pill confidence-pill--${level}`}>{pct}%</span>;
}

function ResolveModal({ item, onResolve, onClose, saving, saveError }) {
  const [form, setForm] = useState({ normalizedSkill: item.suggestion?.normalizedSkill ?? "", category: item.suggestion?.category ?? "", notes: "" });
  function handleChange(e) { setForm((prev) => ({ ...prev, [e.target.name]: e.target.value })); }
  function handleSubmit(e) { e.preventDefault(); onResolve({ id: item.id, ...form }); }
  function handleBackdropClick(e) { if (e.target === e.currentTarget) onClose(); }
  return (
    <div className="modal-backdrop" onClick={handleBackdropClick} role="dialog" aria-modal="true" aria-label="Resolve skill">
      <div className="modal-card modal-card--wide">
        <div className="modal-header"><h2 className="modal-title">Resolve Skill</h2><button className="modal-close" onClick={onClose} aria-label="Close">✕</button></div>
        <div className="resolve-context">
          <div className="resolve-context-row"><span className="resolve-label">Raw input</span><span className="resolve-value resolve-value--raw">{item.rawSkill}</span></div>
          {item.suggestion && <div className="resolve-context-row"><span className="resolve-label">Pipeline suggestion</span><span className="resolve-value">{item.suggestion.normalizedSkill}<ConfidencePill value={item.suggestion.confidence} /></span></div>}
          {item.suggestion?.description && <div className="resolve-context-row"><span className="resolve-label">Description</span><span className="resolve-value resolve-value--muted">{item.suggestion.description}</span></div>}
        </div>
        {saveError && <div className="modal-error" role="alert"><strong>Could not resolve.</strong> {saveError}</div>}
        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="form-field"><label htmlFor="resolve-normalizedSkill">Accept or correct the normalized skill <span className="required">*</span></label><input id="resolve-normalizedSkill" name="normalizedSkill" type="text" value={form.normalizedSkill} onChange={handleChange} placeholder="Normalized skill name" required /><span className="field-hint">Edit this field to override the pipeline suggestion.</span></div>
          <div className="form-field"><label htmlFor="resolve-category">Category</label><input id="resolve-category" name="category" type="text" value={form.category} onChange={handleChange} placeholder="e.g. Data Engineering" /></div>
          <div className="form-field"><label htmlFor="resolve-notes">Resolution notes</label><textarea id="resolve-notes" name="notes" rows={2} value={form.notes} onChange={handleChange} placeholder="Optional: why you accepted or overrode the suggestion…" /></div>
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>Cancel</button>
            <button type="submit" className="btn-resolve" disabled={saving}>{saving ? "Resolving…" : "Confirm resolution"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditUnresolvedModal({ item, onSave, onClose, saving, saveError }) {
  const [inputText, setInputText] = useState(item.rawSkill ?? "");
  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed) return;
    onSave({ id: item.id, input: trimmed });
  }
  function handleBackdropClick(e) { if (e.target === e.currentTarget) onClose(); }
  return (
    <div className="modal-backdrop" onClick={handleBackdropClick} role="dialog" aria-modal="true" aria-label="Edit unresolved skill">
      <div className="modal-card">
        <div className="modal-header">
          <h2 className="modal-title">Edit Unresolved Skill</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {saveError && <div className="modal-error" role="alert"><strong>Could not update.</strong> {saveError}</div>}
        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="edit-unresolved-input">Raw Input <span className="required">*</span></label>
            <input
              id="edit-unresolved-input"
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Correct the skill name…"
              required
              autoFocus // eslint-disable-line jsx-a11y/no-autofocus
            />
            <span className="field-hint">Correct the raw input text for this unresolved skill.</span>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving || !inputText.trim()}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Promote-to-org-skill modal ────────────────────────────────────────────────
function AddToOrgSkillsModal({ item, onSave, onClose, saving, saveError, token }) {
  const [form, setForm] = useState({
    rawSkill:        item.rawSkill ?? "",
    normalizedSkill: "",
    category:        "",
    description:     "",
  });
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    fetchCategories(token).then(setCategories);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleChange(e) { setForm((prev) => ({ ...prev, [e.target.name]: e.target.value })); }
  function handleSubmit(e) {
    e.preventDefault();
    onSave({ unresolvedId: item.id, skill: form });
  }
  function handleBackdropClick(e) { if (e.target === e.currentTarget) onClose(); }

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick} role="dialog" aria-modal="true" aria-label="Add to Organisation Skills">
      <div className="modal-card modal-card--wide">
        <div className="modal-header">
          <h2 className="modal-title">Add to Organisation Skills</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="resolve-context">
          <div className="resolve-context-row">
            <span className="resolve-label">Unresolved input</span>
            <span className="resolve-value resolve-value--raw">{item.rawSkill}</span>
          </div>
        </div>
        {saveError && <div className="modal-error" role="alert"><strong>Could not add skill.</strong> {saveError}</div>}
        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="promote-rawSkill">Raw Skill <span className="required">*</span></label>
            <input id="promote-rawSkill" name="rawSkill" type="text" value={form.rawSkill} onChange={handleChange} placeholder="e.g. react.js" required />
            <span className="field-hint">The skill as it appears in your organisation's data.</span>
          </div>
          <div className="form-field">
            <label htmlFor="promote-normalizedSkill">Normalized Skill <span className="required">*</span></label>
            <input id="promote-normalizedSkill" name="normalizedSkill" type="text" value={form.normalizedSkill} onChange={handleChange} placeholder="e.g. React" required />
            <span className="field-hint">The canonical standardised name for this skill.</span>
          </div>
          <div className="form-field">
            <label htmlFor="promote-category">Category <span className="required">*</span></label>
            <select id="promote-category" name="category" value={form.category} onChange={handleChange} required>
              <option value="">— select a category —</option>
              {categories.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
            </select>
            <span className="field-hint">Choose from the canonical catalogue categories.</span>
          </div>
          <div className="form-field">
            <label htmlFor="promote-description">Description</label>
            <textarea id="promote-description" name="description" rows={2} value={form.description} onChange={handleChange} placeholder="Optional description…" />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Adding…" : "Add to Organisation Skills"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Access denied panel ───────────────────────────────────────────────────────
function AccessDeniedPage() {
  return (
    <div className="placeholder-page">
      <div className="placeholder-inner">
        <div className="placeholder-icon" aria-hidden="true">🔒</div>
        <h2>Access Denied</h2>
        <p>This section is restricted to Admin accounts. Contact your administrator if you believe this is an error.</p>
      </div>
    </div>
  );
}

// ── Role guard — delegates so hooks are always called unconditionally ──────────
function UnresolvedPage({ session }) {
  if (session.role !== "Admin") return <AccessDeniedPage />;
  return <UnresolvedAdminPage session={session} />;
}

// ── Admin-only implementation (hooks always run here) ─────────────────────────
function UnresolvedAdminPage({ session }) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  const [editTarget, setEditTarget]       = useState(null);
  const [editing, setEditing]             = useState(false);
  const [editError, setEditError]         = useState(null);
  const [promoteTarget, setPromoteTarget] = useState(null);
  const [promoting, setPromoting]         = useState(false);
  const [promoteError, setPromoteError]   = useState(null);

  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 400); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(1); }, [debouncedSearch]);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { const data = await fetchUnresolvedSkills({ search: debouncedSearch, page, token: session.token }); setItems(data.items ?? []); setTotal(data.total ?? 0); }
    catch (err) { setError(err.message || "An unexpected error occurred."); setItems([]); setTotal(0); }
    finally { setLoading(false); }
  }, [session.orgId, debouncedSearch, page]);

  useEffect(() => { load(); }, [load]);

  async function handleEdit(payload) {
    setEditing(true); setEditError(null);
    try { await updateUnresolvedSkill({ id: payload.id, input: payload.input, token: session.token }); setEditTarget(null); load(); }
    catch (err) { setEditError(err.message || "An unexpected error occurred."); }
    finally { setEditing(false); }
  }

  async function handleDelete(item) {
    if (!window.confirm("Delete this unresolved record permanently?")) return;
    try { await deleteUnresolvedSkill({ id: item.id, token: session.token }); load(); }
    catch (err) { alert(`Delete failed: ${err.message}`); }
  }

  async function handlePromote(payload) {
    setPromoting(true); setPromoteError(null);
    try {
      await promoteUnresolved({ unresolvedId: payload.unresolvedId, skill: payload.skill, token: session.token });
      setPromoteTarget(null);
      load();
    }
    catch (err) { setPromoteError(err.message || "An unexpected error occurred."); }
    finally { setPromoting(false); }
  }

  return (
    <div className="page">
      <div className="page-header"><div><h1 className="page-title">Unresolved Skills</h1><p className="page-subtitle">Skills from <strong>{session.orgName}</strong> that the pipeline could not confidently match.&ensp;{!loading && !error && <span>{total.toLocaleString()} pending</span>}</p></div></div>
      <div className="toolbar"><SearchBar id="unresolved-search" value={search} onChange={setSearch} placeholder="Search unresolved skills…" label="Search unresolved skills" /></div>
      {loading && <div className="state-loading" aria-live="polite"><span className="spinner" aria-hidden="true" />Loading unresolved skills…</div>}
      {!loading && error && <div className="state-error" role="alert"><strong>Could not load unresolved skills.</strong><p>{error}</p><button className="retry-btn" onClick={load}>Try again</button></div>}
      {!loading && !error && (
        <>
          {items.length === 0
            ? <div className="table-empty table-empty--success"><p>🎉 No unresolved skills — everything has been reviewed.</p></div>
            : (
              <div className="table-wrapper">
                <table className="data-table" aria-label="Unresolved skills">
                  <thead><tr><th scope="col">Raw Input</th><th scope="col">Suggested Match</th><th scope="col">Category</th><th scope="col">Confidence</th><th scope="col" className="th-actions">Actions</th></tr></thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.id}>
                        <td className="cell-raw">{item.rawSkill}</td>
                        <td className="cell-skill">{item.suggestion?.normalizedSkill ?? <span className="cell-empty">No suggestion</span>}</td>
                        <td>{item.suggestion?.category ? <span className="category-tag">{item.suggestion.category}</span> : <span className="cell-empty">—</span>}</td>
                        <td>{item.suggestion?.confidence != null ? <ConfidencePill value={item.suggestion.confidence} /> : <span className="cell-empty">—</span>}</td>
                        <td className="cell-actions">
                          <button className="action-btn action-btn--resolve" onClick={() => { setPromoteTarget(item); setPromoteError(null); }} aria-label={`Add ${item.rawSkill} to organisation skills`}>Add to Org Skills</button>
                          <button className="action-btn action-btn--edit" onClick={() => { setEditTarget(item); setEditError(null); }} aria-label={`Edit ${item.rawSkill}`}>Edit</button>
                          <button className="action-btn action-btn--delete" onClick={() => handleDelete(item)} aria-label={`Delete ${item.rawSkill}`}>Delete</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
          <Paginator page={page} total={total} pageSize={PAGE_SIZE} onPrev={() => setPage((p) => p - 1)} onNext={() => setPage((p) => p + 1)} />
        </>
      )}
      {editTarget && <EditUnresolvedModal item={editTarget} onSave={handleEdit} onClose={() => { setEditTarget(null); setEditError(null); }} saving={editing} saveError={editError} />}
      {promoteTarget && <AddToOrgSkillsModal item={promoteTarget} onSave={handlePromote} onClose={() => { setPromoteTarget(null); setPromoteError(null); }} saving={promoting} saveError={promoteError} token={session.token} />}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// NORMALIZATION OUTPUT PAGE
// ══════════════════════════════════════════════════════════════════════════════

async function fetchOutputResults({ search, status, page, token }) {
  const params = new URLSearchParams();
  if (search) params.set("q", search);
  if (status) params.set("status", status);
  params.set("page",  String(page));
  params.set("limit", String(PAGE_SIZE));
  return apiRequest(`/api/v1/organizations/me/history?${params.toString()}`, { token });
}

// ── Status badge ──────────────────────────────────────────────────────────────
const STATUS_META = {
  resolved:   { label: "Resolved",   cls: "status--resolved"   },
  unresolved: { label: "Unresolved", cls: "status--unresolved" },
  pending:    { label: "Pending",    cls: "status--pending"    },
  matched:    { label: "Matched",    cls: "status--resolved"   },
};

function StatusBadge({ value }) {
  const meta = STATUS_META[value?.toLowerCase()] ?? { label: value ?? "—", cls: "status--unknown" };
  return <span className={`status-badge ${meta.cls}`}>{meta.label}</span>;
}

// ── CSV export (client-side, no extra library) ────────────────────────────────
function exportCsv(items) {
  const headers = ["Input Skill", "Normalized Skill", "Version", "Category", "Description", "Status"];
  const rows = items.map((item) => [
    item.inputSkill      ?? "",
    item.normalizedSkill ?? "",
    item.version         ?? "",
    item.category        ?? "",
    item.description     ?? "",
    item.status          ?? "",
  ]);

  const escape = (val) => `"${String(val).replace(/"/g, '""')}"`;
  const csv = [headers, ...rows].map((r) => r.map(escape).join(",")).join("\r\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `normalization-output-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Main OutputPage component ─────────────────────────────────────────────────
function OutputPage({ session, outputCache, setOutputCache }) {
  const [search, setSearch]   = useState("");
  const [status, setStatus]   = useState("");
  const [page, setPage]       = useState(1);
  // Initialise from lifted cache so navigating back restores last results.
  const [items, setItems]     = useState(outputCache.items);
  const [total, setTotal]     = useState(outputCache.total);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [debouncedSearch, setDebouncedSearch] = useState(search);

  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 400); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(1); }, [debouncedSearch, status]);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await fetchOutputResults({ search: debouncedSearch, status, page, token: session.token });
      const newItems = data.items ?? [];
      const newTotal = data.total ?? 0;
      setItems(newItems);
      setTotal(newTotal);
      setOutputCache({ items: newItems, total: newTotal });
    } catch (err) {
      setError(err.message || "An unexpected error occurred.");
      setItems([]); setTotal(0);
    } finally { setLoading(false); }
  }, [session.orgId, debouncedSearch, status, page]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Normalization Output</h1>
          <p className="page-subtitle">
            Results for <strong>{session.orgName}</strong>.&ensp;
            {!loading && !error && <span>{total.toLocaleString()} {total === 1 ? "result" : "results"}</span>}
          </p>
        </div>
        {/* Export button — only shown when there is data to export */}
        {items.length > 0 && (
          <button
            id="export-csv-btn"
            className="btn-secondary btn-export"
            onClick={() => exportCsv(items)}
            title="Download current page as CSV"
          >
            ↓ Export CSV
          </button>
        )}
      </div>

      {/* Toolbar: search + status filter */}
      <div className="toolbar">
        <SearchBar id="output-search" value={search} onChange={setSearch} placeholder="Search results…" label="Search normalization output" />
        <div className="toolbar-filter">
          <label htmlFor="output-status" className="sr-only">Filter by status</label>
          <select id="output-status" className="toolbar-select" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="matched">Matched</option>
            <option value="unresolved">Unresolved</option>
          </select>
        </div>
      </div>

      {/* States */}
      {loading && <div className="state-loading" aria-live="polite"><span className="spinner" aria-hidden="true" />Loading results…</div>}
      {!loading && error && (
        <div className="state-error" role="alert">
          <strong>Could not load normalization output.</strong>
          <p>{error}</p>
          <button className="retry-btn" onClick={load}>Try again</button>
        </div>
      )}
      {!loading && !error && (
        <>
          {items.length === 0
            ? <div className="table-empty"><p>No results matched your search. Try different keywords or clear the status filter.</p></div>
            : (
              <div className="table-wrapper">
                <table className="data-table" aria-label="Normalization output">
                  <thead>
                    <tr>
                      <th scope="col">Input Skill</th>
                      <th scope="col">Normalized Skill</th>
                      <th scope="col">Version</th>
                      <th scope="col">Category</th>
                      <th scope="col">Description</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.id}>
                        <td className="cell-raw">{item.inputSkill ?? <span className="cell-empty">—</span>}</td>
                        <td className="cell-skill">{item.normalizedSkill ?? <span className="cell-empty">—</span>}</td>
                        <td className="cell-version">{item.version ?? <span className="cell-empty">—</span>}</td>
                        <td>{item.category ? <span className="category-tag">{item.category}</span> : <span className="cell-empty">—</span>}</td>
                        <td className="cell-description">{item.description || <span className="cell-empty">—</span>}</td>
                        <td><StatusBadge value={item.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
          <Paginator page={page} total={total} pageSize={PAGE_SIZE} onPrev={() => setPage((p) => p - 1)} onNext={() => setPage((p) => p + 1)} />
        </>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// NORMALIZE SKILL PAGE
// ══════════════════════════════════════════════════════════════════════════════

// ─────────────────────────────────────────────────────────────────────────────
// API STUB — connect this to your real backend normalization endpoint.
//
// Replace the thrown error with the real fetch call when the endpoint is ready.
//
// Expected request:
//   POST /api/normalize
//   Content-Type: application/json
//   { "skill": "react.js" }
//
// Expected response shape (all fields except normalized_skill are optional):
//   {
//     input_skill,       // string — the skill as submitted
//     normalized_skill,  // string — canonical normalized name
//     version,           // string — e.g. "v2.1"        (optional)
//     category,          // string — skill category      (optional)
//     description,       // string — description text    (optional)
//     status,            // "matched" | "unresolved" | "pending"  (optional)
//   }
//
// Adjust field names above to match your actual API response.
// ─────────────────────────────────────────────────────────────────────────────
async function normalizeSkill({ skill, token }) {
  // Backend accepts { "input": "..." } and returns an array of result objects.
  const data = await apiRequest("/api/v1/normalize", {
    method: "POST",
    token,
    body: JSON.stringify({ input: skill }),
  });
  if (!Array.isArray(data)) {
    throw new Error("The normalization API returned an unexpected response. Expected a list of results.");
  }
  return data;
}

function NormalizeSkillPage({ token }) {
  const [skill, setSkill]               = useState("");
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState(null);
  const [result, setResult]             = useState(null);
  const [validationError, setValidationError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = skill.trim();
    if (!trimmed) {
      setValidationError("Please enter a skill name before submitting.");
      return;
    }
    setValidationError(null);
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await normalizeSkill({ skill: trimmed, token });
      setResult(data);
    } catch (err) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setSkill("");
    setResult(null);
    setError(null);
    setValidationError(null);
  }

  return (
    <div className="page">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Normalize Skill</h1>
          <p className="page-subtitle">
            Enter a skill name or phrase to look up its normalized form, category, and pipeline status.
          </p>
        </div>
      </div>

      {/* Input form */}
      <div className="normalize-form-card">
        <form onSubmit={handleSubmit} noValidate>
          <div className="normalize-form-row">
            <div className="form-field normalize-input-field">
              <label htmlFor="normalize-skill-input">Skill name or phrase</label>
              <input
                id="normalize-skill-input"
                type="text"
                value={skill}
                onChange={(e) => { setSkill(e.target.value); setValidationError(null); }}
                placeholder="e.g. react.js, machine learning, data analysis…"
                disabled={loading}
                autoComplete="off"
                // eslint-disable-next-line jsx-a11y/no-autofocus
                autoFocus
              />
              {validationError && (
                <span className="field-validation-error" role="alert">{validationError}</span>
              )}
            </div>
            <button
              type="submit"
              className="btn-primary normalize-submit-btn"
              disabled={loading}
            >
              {loading
                ? <><span className="spinner spinner--sm" aria-hidden="true" /> Normalizing…</>
                : "Normalize Skill"
              }
            </button>
          </div>
        </form>
      </div>

      {/* API / network error */}
      {!loading && error && (
        <div className="state-error" role="alert">
          <strong>Normalization failed.</strong>
          <p>{error}</p>
          <button className="retry-btn" onClick={() => handleSubmit({ preventDefault: () => {} })}>Try again</button>
        </div>
      )}

      {/* Results */}
      {!loading && result && result.length > 0 && (
        <div className="normalize-results">
          <h2 className="normalize-results-title">
            {result.length === 1 ? "Result" : `${result.length} Results`}
          </h2>
          {result.map((item, idx) => (
            <div key={idx} className="normalize-result-card">
              <dl className="normalize-result-grid">
                <dt>Input Skill</dt>
                <dd className="cell-raw">{item.input || skill}</dd>
                <dt>Normalized Skill</dt>
                <dd className="cell-skill">{item.skill || "Unresolved"}</dd>
                {item.version && <><dt>Version</dt><dd className="cell-version">{item.version}</dd></>}
                {item.category && <><dt>Category</dt><dd><span className="category-tag">{item.category}</span></dd></>}
                {item.description && <><dt>Description</dt><dd className="cell-description">{item.description}</dd></>}
              </dl>
            </div>
          ))}
          <div className="normalize-result-actions">
            <button className="btn-secondary" onClick={handleReset}>Normalize another skill</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// SIDEBAR
// ══════════════════════════════════════════════════════════════════════════════
function Sidebar({ session, activePage, onNavigate, onSignOut }) {
  const visibleNav = NAV_ITEMS.filter((item) => !item.adminOnly || session.role === "Admin");
  return (
    <aside className="sidebar">
      <div className="sidebar-brand"><div className="brand-icon">S</div><span className="brand-name">skillbase</span></div>
      <nav className="sidebar-nav" aria-label="Main navigation">
        <ul role="list">
          {visibleNav.map((item) => (
            <li key={item.id}>
              <button className={`nav-item ${activePage === item.id ? "nav-item--active" : ""}`} onClick={() => onNavigate(item.id)} aria-current={activePage === item.id ? "page" : undefined}>
                <NavIcon id={item.id} />{item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <div className="sidebar-profile">
        <div className="profile-row">
          <div className="profile-avatar" aria-hidden="true">{session.username[0].toUpperCase()}</div>
          <div className="profile-info">
            <span className="profile-username">{session.username}</span>
            <span className={`role-badge role-badge--${session.role.toLowerCase()}`}>{session.role}</span>
          </div>
        </div>
        <p className="profile-org">{session.orgName}<span className="profile-org-id"> ({session.orgId})</span></p>
        <button className="sign-out-btn" onClick={onSignOut}>Sign out</button>
      </div>
    </aside>
  );
}

function NavIcon({ id }) {
  const icons = {
    catalog:      (<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></svg>),
    "org-skills": (<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>),
    unresolved:   (<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>),
    normalize:    (<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>),
    output:       (<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>),
  };
  return icons[id] ?? null;
}

// ══════════════════════════════════════════════════════════════════════════════
// PAGE ROUTER
// ══════════════════════════════════════════════════════════════════════════════
function PageRouter({ pageId, session, outputCache, setOutputCache }) {
  if (pageId === "catalog")    return <CatalogPage session={session} />;
  if (pageId === "org-skills") return <OrgSkillsPage session={session} />;
  if (pageId === "unresolved") return <UnresolvedPage session={session} />;
  if (pageId === "normalize")  return <NormalizeSkillPage token={session.token} />;
  if (pageId === "output")     return <OutputPage session={session} outputCache={outputCache} setOutputCache={setOutputCache} />;
  return null;
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN APP
// ══════════════════════════════════════════════════════════════════════════════
function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [session, setSession] = useState(null);
  const [activePage, setActivePage] = useState("normalize");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState(null);
  // Lifted state for OutputPage cache — persists across navigations.
  const [outputCache, setOutputCache] = useState({ items: [], total: 0 });

  async function handleLogin(event) {
    event.preventDefault();
    setLoginError(null);
    setLoginLoading(true);
    try {
      const auth = await apiRequest("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password }),
      });
      if (!auth.access_token) throw new Error("Login succeeded but the backend did not return an access token.");
      const user = await apiRequest("/api/v1/auth/me", { token: auth.access_token });
      setSession(makeSession(user, auth.access_token));
      setPassword("");
      setActivePage("normalize");
    } catch (err) {
      setLoginError(err.message || "Sign-in failed. Check your username and password.");
    } finally {
      setLoginLoading(false);
    }
  }

  function handleSignOut() {
    setSession(null);
    setUsername("");
    setPassword("");
    setLoginError(null);
    setActivePage("normalize");
    setOutputCache({ items: [], total: 0 });
  }

  if (session === null) {
    return (
      <main className="login-page">
        <section className="login-card">
          <div className="brand"><div className="brand-icon">S</div><span>skillbase</span></div>
          <div className="login-heading"><h1>Welcome back</h1><p>Sign in to your workspace.</p></div>
          <form onSubmit={handleLogin}>
            <label htmlFor="username">Username</label>
            <input id="username" type="text" placeholder="Enter your username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required disabled={loginLoading} />
            <label htmlFor="password">Password</label>
            <div className="password-input">
              <input id="password" type={showPassword ? "text" : "password"} placeholder="Enter your password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required disabled={loginLoading} />
              <button type="button" className="show-password" onClick={() => setShowPassword(!showPassword)} disabled={loginLoading}>{showPassword ? "Hide" : "Show"}</button>
            </div>
            {loginError && <div className="state-error" role="alert"><strong>Sign-in failed.</strong><p>{loginError}</p></div>}
            <button className="login-button" type="submit" disabled={loginLoading}>{loginLoading ? "Signing in…" : "Sign in"}</button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar session={session} activePage={activePage} onNavigate={setActivePage} onSignOut={handleSignOut} />
      <main className="app-main">
        <PageRouter pageId={activePage} session={session} outputCache={outputCache} setOutputCache={setOutputCache} />
      </main>
    </div>
  );
}

export default App;
