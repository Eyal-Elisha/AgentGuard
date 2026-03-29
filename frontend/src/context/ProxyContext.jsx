import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from 'react';

const STORAGE_KEY = 'agentguard-proxy-active';

function readStored() {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

function writeStored(active) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, active ? '1' : '0');
  } catch {
    /* ignore quota / private mode */
  }
}

let proxyActive = readStored();
const listeners = new Set();

function subscribe(callback) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

function getSnapshot() {
  return proxyActive;
}

function setProxyActive(next) {
  const value = typeof next === 'function' ? next(proxyActive) : next;
  if (value === proxyActive) return;
  proxyActive = value;
  writeStored(value);
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
  } catch {
    /* ignore */
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
  } catch {
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

  const setActive = useCallback((next) => {
    const current = getSnapshot();
    const value = typeof next === 'function' ? next(current) : next;
    void (async () => {
      if (value) {
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

  const value = useMemo(
    () => ({
      isProxyActive,
      setProxyActive: setActive,
      toggleProxy,
    }),
    [isProxyActive, setActive, toggleProxy],
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
