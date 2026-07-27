import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore } from 'react';
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

export function deactivateProxy(agentName) {
  if (!proxyActive) return;
  setProxyActive(false);
  void callProxyControl(false, agentName).catch(() => setProxyActive(true));
}

const ProxyContext = createContext(null);

export function ProxyProvider({ children }) {
  const isProxyActive = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const isPassiveMode = useSyncExternalStore(subPass, getPassSnap, getPassSnap);

  useEffect(() => {
    void (async () => {
      const data = await fetchProxyStatus();
      if (data && typeof data.active === 'boolean') setProxyActive(data.active);
    })();
  }, []);

  useEffect(() => { void (async () => { await syncPass(); })(); }, []);

  const toggleProxy = useCallback((agentName) => {
    const next = !getSnapshot();
    void (async () => {
      try { await callProxyControl(next, agentName); setProxyActive(next); } catch (e) { console.error(e); if (!next) setProxyActive(true); }
    })();
  }, []);

  const value = useMemo(() => ({
    isProxyActive, setProxyActive, toggleProxy, isPassiveMode, togglePassiveMode: togglePassAsync,
  }), [isProxyActive, toggleProxy, isPassiveMode]);

  return <ProxyContext.Provider value={value}>{children}</ProxyContext.Provider>;
}

export function useProxy() {
  const ctx = useContext(ProxyContext);
  if (!ctx) throw new Error('useProxy must be used within a ProxyProvider');
  return ctx;
}
