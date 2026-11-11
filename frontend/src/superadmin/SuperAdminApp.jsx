import { useState, useEffect, useCallback, createContext, useContext } from "react";
import {
  clearToken, getToken, setToken, login,
  fetchDashboard, fetchOrganizations, updateOrgStatus, deleteOrganization,
  fetchUsers, updateUserStatus,
  fetchSkills, fetchSkillById, fetchSkillAliases, createSkill, updateSkill,
  addSkillAlias, deleteSkillAlias,
  fetchHistory, fetchUnresolved,
  fetchOrgSkillReview, approveOrgSkill, rejectOrgSkill,
} from "./client.js";
import "./SuperAdmin.css";

// ═══════════════════════════════════════════════════════════════════════════
// SVG ICONS
// ═══════════════════════════════════════════════════════════════════════════
const Icons = {
  dashboard: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>,
  organizations: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>,
  users: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  skills: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>,
  history: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
  unresolved: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  review: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>,
  logout: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  search: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  eye: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>,
  chevronDown: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>,
  chevronRight: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>,
  orgActive: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>,
  orgInactive: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  aliases: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>,
  normEvents: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
};

// ═══════════════════════════════════════════════════════════════════════════
// COMPACT NUMBER FORMATTING
// ═══════════════════════════════════════════════════════════════════════════
function formatCount(n) {
  if (n == null) return "—";
  if (n < 10000) return n.toLocaleString();
  if (n < 1000000) { const k = n / 1000; return (Number.isInteger(k) ? k : k.toFixed(1)) + "K"; }
  const m = n / 1000000; return (Number.isInteger(m) ? m : m.toFixed(1)) + "M";
}

// ═══════════════════════════════════════════════════════════════════════════
// HASH ROUTER
// ═══════════════════════════════════════════════════════════════════════════
const RouterCtx = createContext(null);
function Router({ children }) {
  const getHash = () => decodeURIComponent(window.location.hash.slice(1)) || "/super-admin/login";
  const [path, setPath] = useState(getHash);
  useEffect(() => { const h = () => setPath(getHash()); window.addEventListener("hashchange", h); return () => window.removeEventListener("hashchange", h); }, []);
  const navigate = useCallback((to, { replace = false } = {}) => { if (replace) { window.history.replaceState(null, "", "#" + to); window.dispatchEvent(new HashChangeEvent("hashchange")); } else { window.location.hash = to; } }, []);
  return <RouterCtx.Provider value={{ path, navigate }}>{children}</RouterCtx.Provider>;
}
function useRouter() { return useContext(RouterCtx); }
function NavLink({ to, className, activeClass, children }) {
  const { path, navigate } = useRouter();
  const isActive = path === to || path.startsWith(to);
  return <a href={"#" + to} className={`${className}${isActive ? " " + activeClass : ""}`} onClick={(e) => { e.preventDefault(); navigate(to); }}>{children}</a>;
}
function RequireAuth({ children }) {
  const { navigate, path } = useRouter();
  useEffect(() => {
    if (!getToken()) {
      // No SA token: send the user back to the unified login page.
      // We use navigate to /super-admin/login (the SA login page) which itself
      // has a link back to the org login if needed.
      navigate("/super-admin/login", { replace: true });
    }
  }, [path, navigate]);
  if (!getToken()) return null;
  return children;
}

// ═══════════════════════════════════════════════════════════════════════════
// LAYOUT
// ═══════════════════════════════════════════════════════════════════════════
const NAV_ITEMS = [
  { to: "/super-admin/dashboard",             label: "Dashboard",             icon: Icons.dashboard },
  { to: "/super-admin/organizations",         label: "Organizations",         icon: Icons.organizations },
  { to: "/super-admin/users",                 label: "Users",                 icon: Icons.users },
  { to: "/super-admin/skills",                label: "Skill Catalogue",       icon: Icons.skills },
  { to: "/super-admin/org-skill-review",      label: "Skill Review",          icon: Icons.review },
  { to: "/super-admin/normalization-history", label: "Normalization History", icon: Icons.history },
  { to: "/super-admin/unresolved-skills",     label: "Unresolved Skills",     icon: Icons.unresolved },
];

function Layout({ children }) {
  const { navigate } = useRouter();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">{Icons.skills}</div>
          <div className="sidebar-brand-text"><span>SkillBase</span><span className="sidebar-brand-sub">Super Admin</span></div>
        </div>
        <nav className="sidebar-nav"><ul>
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <li key={to}><NavLink to={to} className="nav-item" activeClass="nav-item--active">{icon}{label}</NavLink></li>
          ))}
        </ul></nav>
        <div className="sidebar-footer">
          <button className="sign-out-btn" onClick={() => {
            clearToken();
            // After SA logout, go back to the unified org login page.
            window.history.replaceState(null, "", "/");
            window.location.reload();
          }}>
            {Icons.logout} Sign out
          </button>
        </div>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SHARED UI COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════
function Toast({ message, type = "success", onDismiss, durationMs = 3500 }) {
  useEffect(() => { if (!message) return; const t = setTimeout(onDismiss, durationMs); return () => clearTimeout(t); }, [message, durationMs, onDismiss]);
  if (!message) return null;
  return <div className={`toast toast--${type}`} role="status" aria-live="polite">{message}<button className="toast-close" onClick={onDismiss} aria-label="Dismiss">✕</button></div>;
}

function ConfirmDialog({ message, onConfirm, onCancel, confirmLabel = "Confirm", danger = false }) {
  return (
    <div className="modal-backdrop" onClick={onCancel} role="dialog" aria-modal="true">
      <div className="modal-card modal-card--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header"><h2 className="modal-title">Confirm</h2></div>
        <p className="confirm-message">{message}</p>
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onCancel}>Cancel</button>
          <button className={danger ? "btn-danger" : "btn-primary"} onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

function Paginator({ page, totalPages, total, onPrev, onNext }) {
  return (
    <div className="paginator">
      {total != null && <span className="paginator-info">{total.toLocaleString()} items</span>}
      <div className="paginator-controls">
        <button className="paginator-btn" disabled={page <= 1} onClick={onPrev}>← Prev</button>
        <span className="paginator-page">Page {page} of {totalPages}</span>
        <button className="paginator-btn" disabled={page >= totalPages} onClick={onNext}>Next →</button>
      </div>
    </div>
  );
}

function SearchToolbar({ value, onChange, placeholder, children }) {
  return (
    <div className="toolbar toolbar--multi">
      <div className="toolbar-search">
        <span className="toolbar-search-icon">{Icons.search}</span>
        <input className="toolbar-input" type="search" placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} />
      </div>
      {children}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = { matched: "status--matched", unresolved: "status--unresolved", overridden: "status--overridden", pending: "status--pending", approved: "status--active", rejected: "status--deleted", not_submitted: "status--unknown" };
  const labels = { not_submitted: "Not Submitted", pending: "Pending", approved: "Approved", rejected: "Rejected", matched: "Matched", unresolved: "Unresolved", overridden: "Overridden" };
  return <span className={`status-badge ${map[status] ?? "status--unknown"}`}>{labels[status] ?? status ?? "—"}</span>;
}

// ═══════════════════════════════════════════════════════════════════════════
// LOGIN PAGE
// ═══════════════════════════════════════════════════════════════════════════
function LoginPage() {
  const { navigate } = useRouter();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => { if (getToken()) navigate("/super-admin/dashboard", { replace: true }); }, [navigate]);
  async function handleSubmit(e) {
    e.preventDefault(); setError(null); setLoading(true);
    try {
      // Use the unified login endpoint so this page also works for SA users
      // who navigate directly to /super-admin/login.
      const data = await fetch("/api/v1/auth/unified-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: form.username.trim(), password: form.password }),
      });
      if (!data.ok) {
        const j = await data.json().catch(() => ({}));
        throw new Error(j?.detail || `HTTP ${data.status}`);
      }
      const auth = await data.json();
      if (auth.user_type !== "super_admin") {
        // Non-SA credentials entered here — send them to the org login page.
        window.history.replaceState(null, "", "/");
        window.location.reload();
        return;
      }
      // Store SA token (via setToken so getToken() works immediately) and navigate.
      setToken(auth.access_token);
      navigate("/super-admin/dashboard", { replace: true });
    }
    catch (err) { setError(err.message || "Login failed."); }
    finally { setLoading(false); }
  }
  return (
    <div className="login-page"><div className="login-card">
      <div className="brand"><div className="brand-icon">{Icons.skills}</div><span>SkillBase</span></div>
      <div className="login-heading"><h1>Welcome back</h1><p>Sign in to continue <span className="login-badge">Super Admin</span></p></div>
      {error && <div className="login-error" role="alert">{error}</div>}
      <form className="login-form" onSubmit={handleSubmit}>
        <div className="form-field"><label htmlFor="un">Username</label><input id="un" type="text" value={form.username} onChange={(e) => setForm(p => ({...p, username: e.target.value}))} placeholder="Username" required autoFocus /></div>
        <div className="form-field"><label htmlFor="pw">Password</label><input id="pw" type="password" value={form.password} onChange={(e) => setForm(p => ({...p, password: e.target.value}))} placeholder="••••••••" required /></div>
        <button type="submit" className="login-submit" disabled={loading}>{loading ? "Signing in…" : "Sign In"}</button>
      </form>
      <div style={{ marginTop: "16px", textAlign: "center", fontSize: "13px", color: "var(--muted)" }}>
        Not a Super Admin?{" "}
        <a href="/" style={{ color: "var(--accent)", textDecoration: "none" }} onClick={(e) => { e.preventDefault(); window.history.replaceState(null, "", "/"); window.location.reload(); }}>
          Go to organisation login
        </a>
      </div>
    </div></div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════
function StatCard({ label, value, icon, to }) {
  const { navigate } = useRouter();
  const formatted = formatCount(value);
  const exact = value != null && value >= 10000 ? value.toLocaleString() : null;
  const inner = <div className="stat-card"><div className="stat-icon">{icon}</div><div className="stat-body"><div className="stat-value" title={exact ?? undefined}>{formatted}</div><div className="stat-label">{label}</div></div></div>;
  return to ? <a href={"#" + to} className="stat-card" onClick={(e) => { e.preventDefault(); navigate(to); }}>{inner}</a> : inner;
}

function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { fetchDashboard().then((d) => setStats(d.stats)).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
  return (
    <div className="page">
      <div className="page-header"><div><h1 className="page-title">Dashboard</h1><p className="page-subtitle">System-wide statistics at a glance.</p></div></div>
      {loading && <div className="state-loading"><span className="spinner" />Loading…</div>}
      {error && <div className="state-error"><strong>Could not load stats.</strong><p>{error}</p></div>}
      {stats && <div className="stat-grid">
        <StatCard label="Total Organizations"    value={stats.total_organizations}    icon={Icons.organizations} to="/super-admin/organizations" />
        <StatCard label="Active Organizations"   value={stats.active_organizations}   icon={Icons.orgActive} />
        <StatCard label="Inactive Organizations" value={stats.inactive_organizations} icon={Icons.orgInactive} />
        <StatCard label="Total Users"            value={stats.total_users}            icon={Icons.users}         to="/super-admin/users" />
        <StatCard label="Canonical Skills"       value={stats.total_skills}           icon={Icons.skills}        to="/super-admin/skills" />
        <StatCard label="Total Aliases"          value={stats.total_aliases}          icon={Icons.aliases} />
        <StatCard label="Normalization Events"   value={stats.total_normalizations}   icon={Icons.normEvents}    to="/super-admin/normalization-history" />
        <StatCard label="Unresolved Skills"      value={stats.total_unresolved}       icon={Icons.unresolved}    to="/super-admin/unresolved-skills" />
      </div>}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ORGANIZATIONS — no Skills column
// ═══════════════════════════════════════════════════════════════════════════
function OrganizationsPage() {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [search, setSearch] = useState("");
  const load = useCallback(() => { setLoading(true); setError(null); fetchOrganizations().then((d) => setOrgs(d.organizations ?? [])).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
  useEffect(() => { load(); }, [load]);
  async function handleToggle(org) {
    try { await updateOrgStatus(org.id, !org.is_active); setToast({ message: `Organization ${org.is_active ? "deactivated" : "activated"}.`, type: "success" }); load(); }
    catch (err) { setToast({ message: err.message, type: "error" }); }
  }
  async function handleDelete(org) {
    try { await deleteOrganization(org.id); setToast({ message: `"${org.name}" deleted.`, type: "success" }); load(); }
    catch (err) { setToast({ message: err.message, type: "error" }); }
    finally { setConfirm(null); }
  }
  const filtered = orgs.filter((o) => !search || o.name.toLowerCase().includes(search.toLowerCase()));
  return (
    <div className="page">
      <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />
      {confirm?.type === "delete" && <ConfirmDialog message={`Delete "${confirm.org.name}"? This cannot be undone.`} confirmLabel="Delete" danger onConfirm={() => handleDelete(confirm.org)} onCancel={() => setConfirm(null)} />}
      <div className="page-header"><div><h1 className="page-title">Organizations</h1><p className="page-subtitle">{loading ? "" : `${orgs.length} organizations`}</p></div></div>
      <SearchToolbar value={search} onChange={setSearch} placeholder="Search organizations…" />
      {loading && <div className="state-loading"><span className="spinner" />Loading…</div>}
      {!loading && error && <div className="state-error"><strong>Error.</strong><p>{error}</p><button className="retry-btn" onClick={load}>Retry</button></div>}
      {!loading && !error && (filtered.length === 0 ? <div className="table-empty"><p>No organizations found.</p></div> :
        <div className="table-wrapper"><table className="data-table">
          <thead><tr><th>ID</th><th>Name</th><th>Status</th><th>Users</th><th><span className="sr-only">Actions</span></th></tr></thead>
          <tbody>{filtered.map((org) => (
            <tr key={org.id} className={org.deleted_at ? "row--deleted" : ""}>
              <td className="cell-id">{org.id}</td>
              <td className="cell-name">{org.name}{org.deleted_at && <span className="status-badge status--deleted"> deleted</span>}</td>
              <td><span className={`status-badge ${org.is_active ? "status--active" : "status--inactive"}`}>{org.is_active ? "Active" : "Inactive"}</span></td>
              <td>{org.user_count}</td>
              <td className="cell-actions">{!org.deleted_at && (<>
                <button className="action-btn" onClick={() => handleToggle(org)}>{org.is_active ? "Deactivate" : "Activate"}</button>
                <button className="action-btn action-btn--delete" onClick={() => setConfirm({ type: "delete", org })}>Delete</button>
              </>)}</td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// USERS — org-grouped expandable
// ═══════════════════════════════════════════════════════════════════════════
function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState({});
  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetchUsers().then((d) => {
      setUsers(d.users ?? []);
      const ids = [...new Set((d.users ?? []).map((u) => u.organization_id ?? "unassigned"))];
      setExpanded(Object.fromEntries(ids.map((id) => [id, true])));
    }).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);
  async function handleToggle(user) {
    try { await updateUserStatus(user.id, !user.is_active); setToast({ message: `"${user.username}" ${user.is_active ? "deactivated" : "activated"}.`, type: "success" }); load(); }
    catch (err) { setToast({ message: err.message, type: "error" }); }
  }
  const q = search.toLowerCase();
  const filtered = users.filter((u) => !q || u.username.toLowerCase().includes(q) || (u.organization_name || "").toLowerCase().includes(q));
  const groupMap = new Map();
  for (const u of filtered) {
    const key = u.organization_id ?? "unassigned";
    if (!groupMap.has(key)) groupMap.set(key, { id: key, name: u.organization_name || "Unassigned", users: [] });
    groupMap.get(key).users.push(u);
  }
  for (const g of groupMap.values()) g.users.sort((a, b) => a.role === b.role ? a.username.localeCompare(b.username) : a.role === "org_admin" ? -1 : 1);
  const groups = [...groupMap.values()];
  return (
    <div className="page">
      <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />
      <div className="page-header"><div><h1 className="page-title">Users</h1><p className="page-subtitle">{loading ? "" : `${users.length} users across ${groups.length} organizations`}</p></div></div>
      <SearchToolbar value={search} onChange={setSearch} placeholder="Search users or organizations…" />
      {loading && <div className="state-loading"><span className="spinner" />Loading…</div>}
      {!loading && error && <div className="state-error"><strong>Error.</strong><p>{error}</p><button className="retry-btn" onClick={load}>Retry</button></div>}
      {!loading && !error && (groups.length === 0 ? <div className="table-empty"><p>No users found.</p></div> :
        <div className="org-groups">{groups.map((g) => (
          <div key={g.id} className="org-group">
            <button className="org-group-header" onClick={() => setExpanded((p) => ({...p, [g.id]: !p[g.id]}))}>
              <span className="org-group-toggle">{expanded[g.id] ? Icons.chevronDown : Icons.chevronRight}</span>
              <span className="org-group-name">{g.name}</span>
              <span className="org-group-count">{g.users.length} user{g.users.length !== 1 ? "s" : ""}</span>
            </button>
            {expanded[g.id] && <div className="table-wrapper"><table className="data-table">
              <thead><tr><th>Username</th><th>Role</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
              <tbody>{g.users.map((u) => (
                <tr key={u.id}>
                  <td className="cell-name">{u.username}</td>
                  <td><span className={`role-badge ${u.role === "org_admin" ? "role-badge--admin" : "role-badge--user"}`}>{u.role === "org_admin" ? "Admin" : "User"}</span></td>
                  <td><span className={`status-badge ${u.is_active ? "status--active" : "status--inactive"}`}>{u.is_active ? "Active" : "Inactive"}</span></td>
                  <td className="cell-actions"><button className="action-btn" onClick={() => handleToggle(u)}>{u.is_active ? "Deactivate" : "Activate"}</button></td>
                </tr>
              ))}</tbody>
            </table></div>}
          </div>
        ))}</div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SKILL CATALOGUE — paginated, View Aliases + Edit separate
// ═══════════════════════════════════════════════════════════════════════════
const PAGE_SIZE = 25;

/** Read-only modal — fetches aliases on mount */
function ViewAliasesModal({ skill, onClose }) {
  const [aliases, setAliases] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => {
    fetchSkillAliases(skill.id)
      .then((d) => setAliases(d.aliases ?? []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [skill.id]);
  return (
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }} role="dialog" aria-modal="true">
      <div className="modal-card modal-card--wide">
        <div className="modal-header"><h2 className="modal-title">Aliases — {skill.name}</h2><button className="modal-close" onClick={onClose}>✕</button></div>
        {loading && <div className="state-loading"><span className="spinner" />Loading…</div>}
        {error && <div className="modal-error">{error}</div>}
        {aliases && <div className="alias-list">
          {aliases.length === 0
            ? <p className="alias-empty">No aliases for this skill.</p>
            : aliases.map((a) => <div key={a.id} className="alias-item"><span className="alias-chip">{a.alias}</span></div>)
          }
        </div>}
        <div className="modal-actions"><button className="btn-secondary" onClick={onClose}>Close</button></div>
      </div>
    </div>
  );
}

/** Edit modal — fetches full skill with aliases on mount */
function EditSkillModal({ skill, onSave, onClose, onAliasChange, saving, saveError }) {
  const isEdit = Boolean(skill?.id);
  const [form, setForm] = useState({ name: skill?.name ?? "", description: skill?.description ?? "", category: skill?.category ?? "" });
  const [aliases, setAliases] = useState([]);
  const [aliasesLoading, setAliasesLoading] = useState(isEdit);
  const [newAlias, setNewAlias] = useState("");
  const [adding, setAdding] = useState(false);
  const [aliasError, setAliasError] = useState(null);
  const [confirmRemove, setConfirmRemove] = useState(null);

  useEffect(() => {
    if (!isEdit || !skill?.id) return;
    fetchSkillAliases(skill.id)
      .then((d) => setAliases(d.aliases ?? []))
      .catch(() => {})
      .finally(() => setAliasesLoading(false));
  }, [isEdit, skill?.id]);

  function handleChange(e) { setForm((p) => ({ ...p, [e.target.name]: e.target.value })); }
  function handleSubmit(e) { e.preventDefault(); onSave({ id: skill?.id, name: form.name.trim(), description: form.description.trim() || null, category: form.category.trim() || null }); }

  async function handleAddAlias(e) {
    e.preventDefault();
    const alias = newAlias.trim(); if (!alias) return;
    if (aliases.some((a) => a.alias.toLowerCase() === alias.toLowerCase())) { setAliasError("This alias already exists."); return; }
    setAdding(true); setAliasError(null);
    try {
      const res = await addSkillAlias(skill.id, alias);
      const updated = [...aliases, { id: res.alias_id, alias }];
      setAliases(updated); setNewAlias(""); onAliasChange(skill.id, updated);
    } catch (err) { setAliasError(err.message); }
    finally { setAdding(false); }
  }

  async function handleRemoveAlias(item) {
    setAliasError(null);
    try { await deleteSkillAlias(skill.id, item.id); const updated = aliases.filter((a) => a.id !== item.id); setAliases(updated); onAliasChange(skill.id, updated); }
    catch (err) { setAliasError(err.message); }
    finally { setConfirmRemove(null); }
  }

  return (
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }} role="dialog" aria-modal="true">
      {confirmRemove && <ConfirmDialog message={`Remove alias "${confirmRemove.alias}"?`} confirmLabel="Remove" danger onConfirm={() => handleRemoveAlias(confirmRemove)} onCancel={() => setConfirmRemove(null)} />}
      <div className="modal-card modal-card--wide">
        <div className="modal-header"><h2 className="modal-title">{isEdit ? "Edit Skill" : "Add Canonical Skill"}</h2><button className="modal-close" onClick={onClose}>✕</button></div>
        {saveError && <div className="modal-error" role="alert">{saveError}</div>}
        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="form-field"><label>Name <span className="required">*</span></label><input name="name" type="text" value={form.name} onChange={handleChange} placeholder="e.g. Python" required /></div>
          <div className="form-field"><label>Description</label><textarea name="description" rows={3} value={form.description} onChange={handleChange} placeholder="Brief description…" /></div>
          <div className="form-field"><label>Category</label><input name="category" type="text" value={form.category} onChange={handleChange} placeholder="e.g. Programming Languages" /></div>
          {isEdit && <div className="form-field">
            <label>Aliases</label>
            {aliasError && <div className="modal-error" style={{ marginBottom: 8 }}>{aliasError}</div>}
            {aliasesLoading
              ? <div className="state-loading" style={{ padding: "8px 0" }}><span className="spinner" />Loading aliases…</div>
              : <div className="alias-list" style={{ marginBottom: 8 }}>
                  {aliases.length === 0 ? <p className="alias-empty">No aliases yet.</p> : aliases.map((a) => (
                    <div key={a.id} className="alias-item">
                      <span className="alias-chip">{a.alias}</span>
                      {a.id != null && <button type="button" className="alias-remove" onClick={() => setConfirmRemove(a)}>✕</button>}
                    </div>
                  ))}
                </div>
            }
            <form className="alias-add-form" onSubmit={handleAddAlias} style={{ marginTop: 0 }}>
              <input type="text" value={newAlias} onChange={(e) => setNewAlias(e.target.value)} placeholder="Add new alias…" className="alias-add-input" />
              <button type="submit" className="btn-primary" disabled={adding || !newAlias.trim()}>{adding ? "Adding…" : "Add"}</button>
            </form>
          </div>}
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Saving…" : isEdit ? "Save changes" : "Create skill"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SkillsPage() {
  const [skills, setSkills] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [modalMode, setModalMode] = useState(null); // "add" | "edit" | "view"
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 400); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(1); }, [debouncedSearch]);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetchSkills({ search: debouncedSearch, page, limit: PAGE_SIZE })
      .then((d) => { setSkills(d.skills ?? []); setTotal(d.total ?? 0); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [debouncedSearch, page]);

  useEffect(() => { load(); }, [load]);

  async function handleSave(skillData) {
    setSaving(true); setSaveError(null);
    try {
      if (skillData.id) { await updateSkill(skillData.id, { name: skillData.name, description: skillData.description, category: skillData.category }); setToast({ message: "Skill updated.", type: "success" }); }
      else { await createSkill({ name: skillData.name, description: skillData.description, category: skillData.category }); setToast({ message: "Skill created.", type: "success" }); }
      setModalMode(null); setSelectedSkill(null); load();
    } catch (err) { setSaveError(err.message); }
    finally { setSaving(false); }
  }

  function handleAliasChange() { /* aliases stored server-side; no local state to update */ }
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="page">
      <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />
      {modalMode === "view" && selectedSkill && <ViewAliasesModal skill={selectedSkill} onClose={() => { setModalMode(null); setSelectedSkill(null); }} />}
      {(modalMode === "add" || modalMode === "edit") && (
        <EditSkillModal skill={modalMode === "edit" ? selectedSkill : null} onSave={handleSave} onClose={() => { setModalMode(null); setSelectedSkill(null); setSaveError(null); }} onAliasChange={handleAliasChange} saving={saving} saveError={saveError} />
      )}
      <div className="page-header">
        <div><h1 className="page-title">Skill Catalogue</h1><p className="page-subtitle">{loading ? "" : `${total.toLocaleString()} canonical skills`}</p></div>
        <button className="btn-primary" onClick={() => { setSaveError(null); setSelectedSkill(null); setModalMode("add"); }}>+ Add Skill</button>
      </div>
      <SearchToolbar value={search} onChange={setSearch} placeholder="Search skills…" />
      {loading && <div className="state-loading"><span className="spinner" />Loading…</div>}
      {!loading && error && <div className="state-error"><strong>Error.</strong><p>{error}</p><button className="retry-btn" onClick={load}>Retry</button></div>}
      {!loading && !error && (<>
        {skills.length === 0 ? <div className="table-empty"><p>No skills found.</p></div> : (
          <div className="table-wrapper"><table className="data-table">
            <thead><tr><th>Name</th><th>Category</th><th>Description</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>{skills.map((skill) => (
              <tr key={skill.id}>
                <td className="cell-skill">{skill.name}</td>
                <td>{skill.category ? <span className="category-tag">{skill.category}</span> : <span className="cell-empty">—</span>}</td>
                <td className="cell-description">{skill.description || <span className="cell-empty">—</span>}</td>
                <td className="cell-actions">
                  <button className="action-btn" onClick={() => { setSelectedSkill(skill); setModalMode("view"); }}>{Icons.eye} Aliases</button>
                  <button className="action-btn" onClick={() => { setSaveError(null); setSelectedSkill(skill); setModalMode("edit"); }}>Edit</button>
                </td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
        <Paginator page={page} totalPages={totalPages} total={total} onPrev={() => setPage((p) => p - 1)} onNext={() => setPage((p) => p + 1)} />
      </>)}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ORG SKILL REVIEW PAGE
// ═══════════════════════════════════════════════════════════════════════════
function ApproveModal({ skill, onConfirm, onClose, loading, error }) {
  const [form, setForm] = useState({ name: skill.normalizedSkill || "", description: skill.description || "", category: skill.category || "" });
  function handleChange(e) { setForm((p) => ({ ...p, [e.target.name]: e.target.value })); }
  function handleSubmit(e) { e.preventDefault(); onConfirm({ name: form.name.trim() || null, description: form.description.trim() || null, category: form.category.trim() || null }); }
  return (
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }} role="dialog" aria-modal="true">
      <div className="modal-card modal-card--wide">
        <div className="modal-header"><h2 className="modal-title">Approve Skill</h2><button className="modal-close" onClick={onClose}>✕</button></div>
        {error && <div className="modal-error">{error}</div>}
        <p style={{ padding: "0 24px 12px", fontSize: 13, color: "var(--color-muted)" }}>
          Optionally override fields before promoting to the canonical catalogue.
        </p>
        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="form-field"><label>Canonical Name</label><input name="name" value={form.name} onChange={handleChange} placeholder="Canonical skill name" /></div>
          <div className="form-field"><label>Description</label><textarea name="description" rows={2} value={form.description} onChange={handleChange} placeholder="Description…" /></div>
          <div className="form-field"><label>Category</label><input name="category" value={form.category} onChange={handleChange} placeholder="Category…" /></div>
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={loading}>{loading ? "Approving…" : "Approve & Promote"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Org Skill Aliases Modal (read-only, uses already-loaded org skill aliases) ──
function OrgAliasModal({ skillName, aliases, onClose }) {
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label={`Aliases for ${skillName}`}
    >
      <div className="modal-card modal-card--wide">
        <div className="modal-header">
          <h2 className="modal-title">Aliases — {skillName}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="alias-list" style={{ maxHeight: 400, overflowY: "auto", padding: "16px 24px" }}>
          {!aliases || aliases.length === 0
            ? <p className="alias-empty">No aliases for this skill.</p>
            : aliases.map((a, i) => (
                <div key={i} className="alias-item">
                  <span className="alias-chip">{typeof a === "string" ? a : a.alias}</span>
                </div>
              ))
          }
        </div>
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

function OrgSkillReviewPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  // Default to "pending" — this is an approval queue, not an inventory.
  const [statusFilter, setStatusFilter] = useState("pending");
  const [page, setPage] = useState(1);
  const [approveTarget, setApproveTarget] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [aliasModal, setAliasModal] = useState(null); // { name: string, aliases: array }

  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 400); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(1); }, [debouncedSearch, statusFilter]);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetchOrgSkillReview({ search: debouncedSearch, status: statusFilter, page, limit: PAGE_SIZE })
      .then((d) => { setItems(d.items ?? []); setTotal(d.total ?? 0); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [debouncedSearch, statusFilter, page]);

  useEffect(() => { load(); }, [load]);

  async function handleApprove(payload) {
    setActionLoading(true); setActionError(null);
    try {
      const res = await approveOrgSkill(approveTarget.id, payload);
      setToast({
        message: res.created_new
          ? `Promoted to new canonical skill "${res.canonical_name}".`
          : `Associated with existing canonical skill "${res.canonical_name}".`,
        type: "success",
      });
      setApproveTarget(null); load();
    } catch (err) { setActionError(err.message); }
    finally { setActionLoading(false); }
  }

  async function handleReject(skill) {
    setActionLoading(true);
    try {
      await rejectOrgSkill(skill.id);
      setToast({ message: "Submission rejected.", type: "success" });
      setRejectTarget(null); load();
    } catch (err) {
      setToast({ message: err.message, type: "error" });
      setRejectTarget(null);
    } finally { setActionLoading(false); }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // Human-readable label for the current filter's count line
  const filterLabel = {
    pending:  "pending submission",
    approved: "approved submission",
    rejected: "rejected submission",
    "":       "submission",
  }[statusFilter] ?? "submission";

  // Empty-state messages per filter
  const emptyMsg = {
    pending:  "No pending submissions. The review queue is clear.",
    approved: "No approved submissions yet.",
    rejected: "No rejected submissions.",
    "":       "No submissions found.",
  }[statusFilter] ?? "No submissions found.";

  return (
    <div className="page">
      <Toast message={toast?.message} type={toast?.type} onDismiss={() => setToast(null)} />
      {approveTarget && (
        <ApproveModal
          skill={approveTarget}
          onConfirm={handleApprove}
          onClose={() => { setApproveTarget(null); setActionError(null); }}
          loading={actionLoading}
          error={actionError}
        />
      )}
      {rejectTarget && (
        <ConfirmDialog
          message={`Reject the submission of "${rejectTarget.normalizedSkill || rejectTarget.rawSkill}" by ${rejectTarget.organizationName || "this organization"}? The organization skill record will be preserved.`}
          confirmLabel="Reject"
          danger
          onConfirm={() => handleReject(rejectTarget)}
          onCancel={() => setRejectTarget(null)}
        />
      )}

      <div className="page-header">
        <div>
          <h1 className="page-title">Skill Review</h1>
          <p className="page-subtitle">
            Review skill submissions from organizations.{" "}
            {!loading && !error && (
              <span>{total.toLocaleString()} {total === 1 ? filterLabel : filterLabel + "s"}</span>
            )}
          </p>
        </div>
      </div>

      <SearchToolbar value={search} onChange={setSearch} placeholder="Search by skill name or organization…">
        <select className="toolbar-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </SearchToolbar>

      {loading && <div className="state-loading"><span className="spinner" />Loading…</div>}
      {!loading && error && (
        <div className="state-error">
          <strong>Error.</strong><p>{error}</p>
          <button className="retry-btn" onClick={load}>Retry</button>
        </div>
      )}
      {!loading && !error && (<>
        {items.length === 0
          ? <div className="table-empty"><p>{emptyMsg}</p></div>
          : (
            <div className="table-wrapper"><table className="data-table">
              <thead><tr>
                <th>Organization</th>
                <th>Raw Skill</th>
                <th>Normalized Skill</th>
                <th>Description</th>
                <th>Category</th>
                <th>Aliases</th>
                <th>Status</th>
                <th><span className="sr-only">Actions</span></th>
              </tr></thead>
              <tbody>{items.map((item) => (
                <tr key={item.id}>
                  <td>{item.organizationName || <span className="cell-empty">—</span>}</td>
                  <td className="cell-raw">{item.rawSkill || <span className="cell-empty">—</span>}</td>
                  <td className="cell-skill">{item.normalizedSkill || <span className="cell-empty">—</span>}</td>
                  <td className="cell-description">{item.description || <span className="cell-empty">—</span>}</td>
                  <td>{item.category ? <span className="category-tag">{item.category}</span> : <span className="cell-empty">—</span>}</td>
                  <td>
                    {item.aliases && item.aliases.length > 0
                      ? (
                          <button
                            className="alias-view-btn"
                            title={`View ${item.aliases.length} alias${item.aliases.length !== 1 ? "es" : ""}`}
                            aria-label={`View aliases for ${item.normalizedSkill || item.rawSkill}`}
                            onClick={() => setAliasModal({ name: item.normalizedSkill || item.rawSkill || "Skill", aliases: item.aliases })}
                          >
                            {Icons.eye}
                            View Aliases
                          </button>
                        )
                      : <span className="cell-empty">—</span>}
                  </td>
                  <td><StatusBadge status={item.reviewStatus} /></td>
                  <td className="cell-actions">
                    {item.reviewStatus === "pending" && (<>
                      <button className="action-btn" onClick={() => { setActionError(null); setApproveTarget(item); }}>Approve</button>
                      <button className="action-btn action-btn--delete" onClick={() => setRejectTarget(item)}>Reject</button>
                    </>)}
                    {item.reviewStatus !== "pending" && <span className="cell-empty">—</span>}
                  </td>
                </tr>
              ))}</tbody>
            </table></div>
          )
        }
        <Paginator page={page} totalPages={totalPages} total={total} onPrev={() => setPage((p) => p - 1)} onNext={() => setPage((p) => p + 1)} />
      </>)}
      {aliasModal && (
        <OrgAliasModal
          skillName={aliasModal.name}
          aliases={aliasModal.aliases}
          onClose={() => setAliasModal(null)}
        />
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// NORMALIZATION HISTORY
// ═══════════════════════════════════════════════════════════════════════════
function NormalizationHistoryPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 400); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(1); }, [debouncedSearch, status]);
  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetchHistory({ search: debouncedSearch, status, page, limit: PAGE_SIZE })
      .then((d) => { setItems(d.history ?? []); setTotal(d.total ?? 0); })
      .catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [debouncedSearch, status, page]);
  useEffect(() => { load(); }, [load]);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return (
    <div className="page">
      <div className="page-header"><div><h1 className="page-title">Normalization History</h1><p className="page-subtitle">{loading ? "" : `${total.toLocaleString()} events`}</p></div></div>
      <SearchToolbar value={search} onChange={setSearch} placeholder="Search input or skill…">
        <select className="toolbar-select" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {["matched", "unresolved", "overridden"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </SearchToolbar>
      {loading && <div className="state-loading"><span className="spinner" />Loading…</div>}
      {!loading && error && <div className="state-error"><strong>Error.</strong><p>{error}</p><button className="retry-btn" onClick={load}>Retry</button></div>}
      {!loading && !error && (<>
        {items.length === 0 ? <div className="table-empty"><p>No events found.</p></div> : (
          <div className="table-wrapper"><table className="data-table">
            <thead><tr><th>ID</th><th>Original Input</th><th>Normalized Skill</th><th>Version</th><th>Description</th><th>Category</th><th>Status</th><th>Organization</th></tr></thead>
            <tbody>{items.map((item) => (
              <tr key={item.id}>
                <td className="cell-id">{item.id}</td>
                <td className="cell-raw">{item.inputSkill || <span className="cell-empty">—</span>}</td>
                <td className="cell-skill">{item.normalizedSkill || <span className="cell-empty">—</span>}</td>
                <td>{item.version || <span className="cell-empty">—</span>}</td>
                <td className="cell-description">{item.description || <span className="cell-empty">—</span>}</td>
                <td>{item.category ? <span className="category-tag">{item.category}</span> : <span className="cell-empty">—</span>}</td>
                <td><StatusBadge status={item.status} /></td>
                <td>{item.organizationName || <span className="cell-empty">—</span>}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
        <Paginator page={page} totalPages={totalPages} total={total} onPrev={() => setPage((p) => p - 1)} onNext={() => setPage((p) => p + 1)} />
      </>)}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// UNRESOLVED SKILLS
// ═══════════════════════════════════════════════════════════════════════════
function UnresolvedSkillsPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 400); return () => clearTimeout(t); }, [search]);
  useEffect(() => { setPage(1); }, [debouncedSearch]);
  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetchUnresolved({ search: debouncedSearch, page, limit: PAGE_SIZE })
      .then((d) => { setItems(d.unresolved_skills ?? []); setTotal(d.total ?? 0); })
      .catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [debouncedSearch, page]);
  useEffect(() => { load(); }, [load]);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return (
    <div className="page">
      <div className="page-header"><div><h1 className="page-title">Unresolved Skills</h1><p className="page-subtitle">{loading ? "" : `${total.toLocaleString()} unresolved (read-only)`}</p></div></div>
      <SearchToolbar value={search} onChange={setSearch} placeholder="Search unresolved skills…" />
      {loading && <div className="state-loading"><span className="spinner" />Loading…</div>}
      {!loading && error && <div className="state-error"><strong>Error.</strong><p>{error}</p><button className="retry-btn" onClick={load}>Retry</button></div>}
      {!loading && !error && (<>
        {items.length === 0 ? <div className="table-empty"><p>No unresolved skills. Queue is clear.</p></div> : (
          <div className="table-wrapper"><table className="data-table">
            <thead><tr><th>ID</th><th>Original Input</th><th>Organization</th><th>Suggested Skill Name</th><th>Description</th><th>Category</th></tr></thead>
            <tbody>{items.map((item) => { const s = item.suggestion; return (
              <tr key={item.id}>
                <td className="cell-id">{item.id}</td>
                <td className="cell-raw">{item.rawSkill || <span className="cell-empty">—</span>}</td>
                <td>{item.organizationName || <span className="cell-empty">—</span>}</td>
                <td className="cell-skill">{s?.normalizedSkill ?? s?.name ?? <span className="cell-empty">—</span>}</td>
                <td className="cell-description">{s?.description || <span className="cell-empty">—</span>}</td>
                <td>{s?.category ? <span className="category-tag">{s.category}</span> : <span className="cell-empty">—</span>}</td>
              </tr>
            ); })}</tbody>
          </table></div>
        )}
        <Paginator page={page} totalPages={totalPages} total={total} onPrev={() => setPage((p) => p - 1)} onNext={() => setPage((p) => p + 1)} />
      </>)}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// APP ROOT
// ═══════════════════════════════════════════════════════════════════════════
function AppRoutes() {
  const { path } = useRouter();
  if (path === "/super-admin/login" || path === "/" || path === "") return <LoginPage />;
  return (
    <RequireAuth>
      <Layout>
        {path === "/super-admin/dashboard"                      && <DashboardPage />}
        {path.startsWith("/super-admin/organizations")          && <OrganizationsPage />}
        {path.startsWith("/super-admin/users")                  && <UsersPage />}
        {path.startsWith("/super-admin/skills")                 && <SkillsPage />}
        {path.startsWith("/super-admin/org-skill-review")       && <OrgSkillReviewPage />}
        {path.startsWith("/super-admin/normalization-history")  && <NormalizationHistoryPage />}
        {path.startsWith("/super-admin/unresolved-skills")      && <UnresolvedSkillsPage />}
      </Layout>
    </RequireAuth>
  );
}

export default function SuperAdminApp() {
  return <Router><AppRoutes /></Router>;
}
