/**
 * One fetch wrapper for the whole dashboard.
 *
 * Requests always send credentials: authentication is an HttpOnly cookie the
 * frontend can neither read nor forge. A 401 means the session is gone, so the
 * caller is bounced to /login instead of rendering an empty dashboard.
 */

import type {
  ActionResult,
  GuildDetail,
  GuildSettings,
  GuildSummary,
  LogPage,
  ModeInfo,
  User,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: init.body ? { "Content-Type": "application/json" } : undefined,
    ...init,
  });

  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, readError(payload) ?? response.statusText);
  }
  return payload as T;
}

/** FastAPI reports validation errors as a list; flatten it to one line. */
function readError(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const entry = item as { loc?: unknown[]; msg?: string };
        const field = entry.loc?.slice(1).join(".") ?? "";
        return field ? `${field}: ${entry.msg}` : entry.msg;
      })
      .join("; ");
  }
  return null;
}

export const api = {
  mode: () => request<ModeInfo>("/api/auth/mode"),
  me: () => request<User>("/api/me"),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  refreshGuilds: () => request<User>("/api/auth/refresh-guilds", { method: "POST" }),

  guilds: () => request<GuildSummary[]>("/api/guilds"),
  guild: (id: string) => request<GuildDetail>(`/api/guilds/${id}`),

  settings: (id: string) => request<GuildSettings>(`/api/guilds/${id}/settings`),
  updateSettings: (id: string, patch: Partial<GuildSettings>) =>
    request<GuildSettings>(`/api/guilds/${id}/settings`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  logs: (id: string, params: { limit?: number; offset?: number; event_type?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.limit) query.set("limit", String(params.limit));
    if (params.offset) query.set("offset", String(params.offset));
    if (params.event_type) query.set("event_type", params.event_type);
    const suffix = query.toString() ? `?${query}` : "";
    return request<LogPage>(`/api/guilds/${id}/logs${suffix}`);
  },

  verify: (id: string, memberId?: string) =>
    request<ActionResult>(`/api/guilds/${id}/verify`, {
      method: "POST",
      body: JSON.stringify(memberId ? { member_id: memberId } : {}),
    }),

  roleAction: (id: string, action: "add" | "remove", userId: string, roleId: string) =>
    request<ActionResult>(`/api/guilds/${id}/roles/${action}`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, role_id: roleId }),
    }),
};

export const loginUrl = `${BASE}/api/auth/login`;
