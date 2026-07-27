import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { clearToken, decodeToken, getToken, saveToken } from '../api/authToken.js';
import { getApiBaseUrl } from '../api/client.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (token) {
      const decoded = decodeToken(token);
      // Optional: check if token is expired
      if (decoded && decoded.exp * 1000 > Date.now()) {
        setCurrentUser(decoded);
      } else {
        clearToken();
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (username, password) => {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || 'Login failed');
    }

    const { jwt } = await res.json();
    saveToken(jwt);
    const decoded = decodeToken(jwt);
    setCurrentUser(decoded);
  }, []);

  const signup = useCallback(async (username, password) => {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || 'Signup failed');
    }

    return await res.json();
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setCurrentUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ currentUser, login, signup, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
