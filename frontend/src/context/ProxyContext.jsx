import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { AGENT_OPTIONS, ALL_TRAFFIC_AGENT, normalizeAgentName, reconcileAgentSelection } from '../constants/agentOptions.js';
import { subscribe as subPass, getSnapshot as getPassSnap, syncFromServer as syncPass, toggle as togglePassAsync } from './passiveMode.js';
import { getSnapshot, patchAgent, replaceAgents, setSelection, subscribe } from './proxyStore.js';
import { callProxyControl, fetchProxyStatus } from './proxyUtils.js';

const ProxyContext = createContext(null);

export function ProxyProvider({ children }) {
  const { agents, selected } = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const isPassiveMode = useSyncExternalStore(subPass, getPassSnap, getPassSnap);
  // Per agent, absent when idle: 'start' or 'stop' captured at click time so
  // the label stays correct even after that agent's `active` flips mid-request.
  const [pendingActions, setPendingActions] = useState({});

  /** Take live state from the backend, and the ports it actually allocated.
   *
   *  Exposed as well as run on mount, because this provider wraps the router
   *  and so mounts before anyone has signed in: that first call is answered
   *  with a 401. Screens that need it ask again once they are behind the login.
   */
  const refreshStatus = useCallback(async () => {
    const data = await fetchProxyStatus();
    if (!Array.isArray(data?.agents)) return;
    const next = { ...getSnapshot().agents };
    for (const entry of data.agents) {
      const name = normalizeAgentName(entry?.agent_name);
      if (!next[name]) continue;
      next[name] = {
        active: Boolean(entry.active),
        proxyPort: entry.proxy_port ?? next[name].proxyPort,
        adminPort: entry.admin_port ?? next[name].adminPort,
      };
    }
    replaceAgents(next);
  }, []);

  useEffect(() => { void refreshStatus(); }, [refreshStatus]);

  useEffect(() => { void (async () => { await syncPass(); })(); }, []);

  /** Drive one agent to `next`, reporting whether it got there. */
  const driveAgent = useCallback(async (agentName, next) => {
    const name = normalizeAgentName(agentName);
    setPendingActions((prev) => ({ ...prev, [name]: next ? 'start' : 'stop' }));
    const startedAt = Date.now();
    try {
      const result = await callProxyControl(next, name);
      patchAgent(name, {
        active: next,
        ...(result?.proxy_port != null ? { proxyPort: result.proxy_port } : {}),
        ...(result?.admin_port != null ? { adminPort: result.admin_port } : {}),
      });
      return true;
    } catch (e) {
      console.error(e);
      // A failed stop means the instance is probably still up; a failed start
      // leaves it down, which is already what the row shows.
      if (!next) patchAgent(name, { active: true });
      return false;
    } finally {
      // The control call returns in ~0.5s but the proxy keeps warming up; hold
      // the loading state for a minimum so the feedback is always visible.
      const remaining = 800 - (Date.now() - startedAt);
      if (remaining > 0) await new Promise((r) => setTimeout(r, remaining));
      setPendingActions((prev) => {
        const { [name]: _dropped, ...rest } = prev;
        return rest;
      });
    }
  }, []);

  /** The one power button: start every selected agent, or stop them all if
   *  they are already up. Each agent is its own instance, so they go in
   *  parallel and one failure does not hold up the rest. */
  const toggleProxy = useCallback(() => {
    const { agents: current, selected: chosen } = getSnapshot();
    if (chosen.length === 0) return;
    const next = !chosen.every((name) => current[name]?.active);
    const acting = chosen.filter((name) => Boolean(current[name]?.active) !== next);
    void Promise.all(acting.map((name) => driveAgent(name, next)));
  }, [driveAgent]);

  /** Replace the selection. An agent dropped from it stops, so a running
   *  instance is never left behind where nothing on screen accounts for it. */
  const setSelectedAgents = useCallback((nextSelection) => {
    const { agents: current, selected: before } = getSnapshot();
    const chosen = reconcileAgentSelection(before, nextSelection);
    const dropped = before.filter((name) => !chosen.includes(name) && current[name]?.active);
    setSelection(chosen);
    void Promise.all(dropped.map((name) => driveAgent(name, false)));
  }, [driveAgent]);

  const value = useMemo(() => {
    const activeSelected = selected.filter((name) => agents[name]?.active);
    return {
      agents,
      selectedAgents: selected,
      setSelectedAgents,
      // Whether *any* agent is protected, for callers that only need the one bit.
      isProxyActive: AGENT_OPTIONS.some((name) => agents[name]?.active),
      // The power button is on only once everything selected is up.
      isSelectionActive: selected.length > 0 && activeSelected.length === selected.length,
      activeSelectedCount: activeSelected.length,
      // The two modes route differently, so the screen explains a different setup step for each.
      isAllTrafficSelected: selected.includes(ALL_TRAFFIC_AGENT),
      toggleProxy,
      refreshStatus,
      pendingActions,
      // Whichever action the batch is mid-way through, for the button's label.
      pendingSelectionAction: selected.map((name) => pendingActions[name]).find(Boolean) ?? null,
      isPassiveMode,
      togglePassiveMode: togglePassAsync,
    };
  }, [agents, selected, setSelectedAgents, toggleProxy, refreshStatus, pendingActions, isPassiveMode]);

  return <ProxyContext.Provider value={value}>{children}</ProxyContext.Provider>;
}

export function useProxy() {
  const ctx = useContext(ProxyContext);
  if (!ctx) throw new Error('useProxy must be used within a ProxyProvider');
  return ctx;
}
