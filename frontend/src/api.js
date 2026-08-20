async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "请求失败，请稍后重试");
  return body;
}

export const api = {
  login: (payload) => request("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  register: (payload) => request("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  guest: () => request("/api/auth/guest", { method: "POST" }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request("/api/auth/me"),
  health: () => request("/api/health"),
  dashboard: () => request("/api/dashboard"),
  customers: () => request("/api/customers"),
  customer: (id) => request(`/api/customers/${id}`),
  analyse: (payload) => request("/api/analysis", { method: "POST", body: JSON.stringify(payload) }),
  capture: (payload) => request("/api/captures", { method: "POST", body: JSON.stringify(payload) }),
  confirmActionDraft: (draft_id) => request("/api/action-drafts/confirm", { method: "POST", body: JSON.stringify({ draft_id }) }),
  dismissActionDraft: (draft_id) => request("/api/action-drafts/dismiss", { method: "POST", body: JSON.stringify({ draft_id }) }),
  tasks: () => request("/api/tasks?include_done=true"),
  task: (payload) => request("/api/tasks", { method: "POST", body: JSON.stringify(payload) }),
  changeTask: (id, status) => request(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  feedback: (payload) => request("/api/feedback", { method: "POST", body: JSON.stringify(payload) }),
};
