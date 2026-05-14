import { getAccessToken } from "./auth";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  role: "admin" | "user";
  user: { id: string; email: string; org_id?: string };
};

// Default: relatief (= same-origin). Lokaal dev kan NEXT_PUBLIC_API_URL=http://localhost:8000 zetten.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
const BASE = `${API_URL}/api/v1`;

class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`API error ${status}`);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T = void>(path: string) => request<T>(path, { method: "DELETE" }),
};

export { ApiError };
