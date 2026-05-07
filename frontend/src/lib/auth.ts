export type Role = "admin" | "user";

interface Session {
  accessToken: string;
  role: Role;
  userId: string;
  email: string;
  orgId?: string;
}

let _session: Session | null = null;

export function setSession(s: Session) {
  _session = s;
}

export function getSession(): Session | null {
  return _session;
}

export function getAccessToken(): string | null {
  return _session?.accessToken ?? null;
}

export function getRole(): Role | null {
  return _session?.role ?? null;
}

export function clearSession() {
  _session = null;
}

export function isLoggedIn(): boolean {
  return _session !== null;
}
