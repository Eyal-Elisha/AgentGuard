import { jwtDecode } from 'jwt-decode';

const TOKEN_KEY = 'agentguard_jwt';

export function saveToken(token) {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(TOKEN_KEY, token);
  }
}

export function getToken() {
  if (typeof window !== 'undefined') {
    return window.localStorage.getItem(TOKEN_KEY);
  }
  return null;
}

export function clearToken() {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

export function decodeToken(token) {
  if (!token) return null;
  try {
    const parsed = jwtDecode(token);
    return {
      userId: parsed.sub,
      username: parsed.username,
      isAdmin: parsed.is_admin,
      exp: parsed.exp,
    };
  } catch {
    return null;
  }
}
