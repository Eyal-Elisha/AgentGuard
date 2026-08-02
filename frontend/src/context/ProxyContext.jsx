import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { subscribe as subPass, getSnapshot as getPassSnap, syncFromServer as syncPass, toggle as togglePassAsync } from './passiveMode.js';
import { callProxyControl, fetchProxyStatus } from './proxyUtils.js';

const STORAGE_KEY = 'agentguard-proxy-active';
let proxyActive = localStorage.getItem(STORAGE_KEY) === '1';
const listeners = new Set();

function subscribe(callback) { listeners.add(callback); return () => listeners.delete(callback); }
function getSnapshot() { return proxyActive; }
function setProxyActive(value) {
  if (value === proxyActive) return;
  proxyActive = value;
  try { localStorage.setItem(STORAGE_KEY, value ? '1' : '0'); } catch (_) { }
  listeners.forEach((fn) => fn());
}

export function deactivateProxy() {
  if (!proxyActive) return;
  setProxyActive(false);
  void callProxyControl(false).catch(() => setProxyActive(true));
}

const ProxyContext = createContext(null);

export function ProxyProvider({ children }) {
  const isProxyActive = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const isPassiveMode = useSyncExternalStore(subPass, getPassSnap, getPassSnap);
  const [isProxyPending, setIsProxyPending] = useState(false);

  useEffect(() => {
    void (async () => {
      const data = await fetchProxyStatus();
      if (data && typeof data.active === 'boolean') setProxyActive(data.active);
    })();
  }, []);

  useEffect(() => { void (async () => { await syncPass(); })(); }, []);

  const toggleProxy = useCallback(() => {
    const next = !getSnapshot();
    setIsProxyPending(true);
    const startedAt = Date.now();
    void (async () => {
      try { await callProxyControl(next); setProxyActive(next); }
      catch (e) { console.error(e); if (!next) setProxyActive(true); }
      finally {
        // The control call returns in ~0.5s but the proxy keeps warming up;
        // hold the loading state for a minimum so the feedback is always visible.
        const remaining = 800 - (Date.now() - startedAt);
        if (remaining > 0) await new Promise((r) => setTimeout(r, remaining));
        setIsProxyPending(false);
      }
    })();
  }, []);

  const value = useMemo(() => ({
    isProxyActive, setProxyActive, toggleProxy, isProxyPending, isPassiveMode, togglePassiveMode: togglePassAsync,
  }), [isProxyActive, toggleProxy, isProxyPending, isPassiveMode]);

  return <ProxyContext.Provider value={value}>{children}</ProxyContext.Provider>;
}

export function useProxy() {
  const ctx = useContext(ProxyContext);
  if (!ctx) throw new Error('useProxy must be used within a ProxyProvider');
  return ctx;
}
