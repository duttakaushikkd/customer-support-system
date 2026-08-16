const TOKEN_KEY = "css_token";
const USER_KEY = "css_user";

export type SessionUser = {
  username: string;
  email?: string | null;
  role: "admin" | "customer";
  name: string;
  access_token: string;
};

export function saveSession(user: SessionUser) {
  localStorage.setItem(TOKEN_KEY, user.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getSession(): SessionUser | null {
  const raw = localStorage.getItem(USER_KEY);
  const token = localStorage.getItem(TOKEN_KEY);
  if (!raw || !token) return null;
  try {
    const parsed = JSON.parse(raw);
    return {
      ...parsed,
      username: parsed.username || parsed.email,
      access_token: token,
    };
  } catch {
    return null;
  }
}

export function acquireTokenSilent(): string | null {
  return getSession()?.access_token ?? null;
}
