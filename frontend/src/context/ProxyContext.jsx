import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from 'react';
import {
  subscribe as subscribePassiveMode,
  getSnapshot as getPassiveModeSnapshot,
  syncFromServer as syncPassiveModeFromServer,
  toggle as togglePassiveModeAsync,
} from './passiveMode.js';

const STORAGE_KEY = 'agentguard-proxy-active';

let proxyActive = localStorage.getItem(STORAGE_KEY) === '1';
const listeners = new Set();

function subscribe(callback) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

function getSnapshot() {
  return proxyActive;
}

function setProxyActive(value) {
  if (value === proxyActive) return;
  proxyActive = value;
  try {
    localStorage.setItem(STORAGE_KEY, value ? '1' : '0');
  } catch (_) {
    /* ignore quota errors */
  }
  listeners.forEach((fn) => fn());
}

function getApiBase() {
  const raw = import.meta.env.VITE_API_BASE_URL;
  if (raw == null || String(raw).trim() === '') return null;
  return String(raw).trim().replace(/\/$/, '');
}

async function callProxyControl(active) {
  const base = getApiBase();
  if (!base) {
    throw new Error('VITE_API_BASE_URL is not configured');
  }
  const res = await fetch(`${base}/api/proxy/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active }),
  });
  let data = {};
  try {
    data = await res.json();
  } catch (_) {
    /* ignore JSON parse errors */
  }
  if (!res.ok) {
    throw new Error(data.error || res.statusText || 'Proxy control failed');
  }
  return data;
}

async function fetchProxyStatus() {
  const base = getApiBase();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/api/proxy/status`);
    if (!res.ok) return null;
    return res.json();
  } catch (_) {
    return null;
  }
}

/** Turns proxy off (e.g. when the protected agent changes). */
export function deactivateProxy() {
  if (!proxyActive) return;
  setProxyActive(false);
  void callProxyControl(false).catch(() => {
    setProxyActive(true);
  });
}

const ProxyContext = createContext(null);

export function ProxyProvider({ children }) {
  const isProxyActive = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const isPassiveMode = useSyncExternalStore(subscribePassiveMode, getPassiveModeSnapshot, getPassiveModeSnapshot);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const data = await fetchProxyStatus();
      if (cancelled || data == null || typeof data.active !== 'boolean') return;
      setProxyActive(data.active);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      await syncPassiveModeFromServer();
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleProxy = useCallback(() => {
    const current = getSnapshot();
    const next = !current;
    void (async () => {
      if (next) {
        try {
          await callProxyControl(true);
          setProxyActive(true);
        } catch (e) {
          console.error(e);
        }
      } else {
        setProxyActive(false);
        try {
          await callProxyControl(false);
        } catch (e) {
          console.error(e);
          setProxyActive(true);
        }
      }
    })();
  }, []);

  const togglePassiveMode = useCallback(togglePassiveModeAsync, []);

  const value = useMemo(
    () => ({
      isProxyActive,
      setProxyActive: setProxyActive,
      toggleProxy,
      isPassiveMode,
      togglePassiveMode,
    }),
    [isProxyActive, toggleProxy, isPassiveMode, togglePassiveMode],
  );

  return (
    <ProxyContext.Provider value={value}>{children}</ProxyContext.Provider>
  );
}

export function useProxy() {
  const ctx = useContext(ProxyContext);
  if (ctx == null) {
    throw new Error('useProxy must be used within a ProxyProvider');
  }
  return ctx;
}
