import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from 'react';
import { AGENT_OPTIONS } from '../constants/agentOptions.js';
import { deactivateProxy } from './ProxyContext.jsx';

const STORAGE_KEY = 'agentguard-selected-agent';

function readStored() {
  if (typeof window === 'undefined') return AGENT_OPTIONS[0];
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    if (v != null && AGENT_OPTIONS.includes(v)) return v;
  } catch {
    /* ignore */
  }
  return AGENT_OPTIONS[0];
}

function writeStored(agent) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, agent);
  } catch {
    /* ignore */
  }
}

let selectedAgent = readStored();
const listeners = new Set();

function subscribe(callback) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

function getSnapshot() {
  return selectedAgent;
}

function setSelectedAgent(next) {
  const value = typeof next === 'function' ? next(selectedAgent) : next;
  if (!AGENT_OPTIONS.includes(value)) return;
  if (value === selectedAgent) return;
  selectedAgent = value;
  writeStored(value);
  deactivateProxy();
  listeners.forEach((fn) => fn());
}

const AgentContext = createContext(null);

export function AgentProvider({ children }) {
  const agent = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  const setAgent = useCallback((next) => {
    setSelectedAgent(next);
  }, []);

  const value = useMemo(
    () => ({
      selectedAgent: agent,
      setSelectedAgent: setAgent,
    }),
    [agent, setAgent],
  );

  return (
    <AgentContext.Provider value={value}>{children}</AgentContext.Provider>
  );
}

export function useAgent() {
  const ctx = useContext(AgentContext);
  if (ctx == null) {
    throw new Error('useAgent must be used within an AgentProvider');
  }
  return ctx;
}
