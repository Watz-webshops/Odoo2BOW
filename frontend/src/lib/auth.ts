export type Role = "admin" | "user";

interface Session {
  accessToken: string;
  role: Role;
  userId: string;
  email: string;
  orgId?: string;
}

const STORAGE_KEY = "odoo2bow.session";

function loadFromStorage(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

let _session: Session | null = loadFromStorage();

export function setSession(s: Session) {
  _session = s;
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    } catch {
      // localStorage kan geblokkeerd zijn (private mode, quota); negeer.
    }
  }
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
  if (typeof window !== "undefined") {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // negeer
    }
  }
}

export function isLoggedIn(): boolean {
  return _session !== null;
}
