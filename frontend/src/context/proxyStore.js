import {
  AGENT_OPTIONS,
  defaultPortsForAgent,
  normalizeAgentName,
  resolveStoredAgents,
} from '../constants/agentOptions.js';

/** The proxy state behind useSyncExternalStore: which agents are up, and which
 *  the power button acts on. Kept outside the provider, the way passiveMode.js
 *  is, so a module can read or nudge it without a React tree. */

const AGENTS_KEY = 'agentguard-proxy-agents';
const SELECTION_KEY = 'agentguard-selected-agents';

/** One entry per agent: whether its proxy is up, and the endpoint it serves.
 *  Ports are deterministic, so they start at the allocation the catalogue
 *  implies rather than at null and wait for the backend to confirm them. */
function blankAgents() {
  return Object.fromEntries(
    AGENT_OPTIONS.map((name) => [
      name,
      { active: false, browserError: null, ...defaultPortsForAgent(name) },
    ]),
  );
}

/** Last known state, so the screen is not blank while the status call is out. */
function readStored() {
  const agents = blankAgents();
  let stored = null;
  try {
    const raw = JSON.parse(localStorage.getItem(AGENTS_KEY) ?? '{}');
    for (const name of AGENT_OPTIONS) {
      if (raw?.[name]?.active) agents[name] = { ...agents[name], active: true };
    }
    stored = JSON.parse(localStorage.getItem(SELECTION_KEY) ?? 'null');
  } catch (_) { /* ignore */ }
  return { agents, selected: resolveStoredAgents(stored) };
}

let state = readStored();
const listeners = new Set();

export function subscribe(callback) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

export function getSnapshot() {
  return state;
}

function publish(next) {
  state = next;
  try {
    localStorage.setItem(AGENTS_KEY, JSON.stringify(next.agents));
    localStorage.setItem(SELECTION_KEY, JSON.stringify(next.selected));
  } catch (_) { }
  listeners.forEach((fn) => fn());
}

/** Merge a patch into one agent's entry, leaving every other agent untouched. */
export function patchAgent(agentName, patch) {
  const name = normalizeAgentName(agentName);
  const current = state.agents[name];
  if (!current) return;
  const merged = { ...current, ...patch };
  if (Object.keys(merged).every((key) => merged[key] === current[key])) return;
  publish({ ...state, agents: { ...state.agents, [name]: merged } });
}

/** Replace every agent's entry at once, from a status response. */
export function replaceAgents(agents) {
  publish({ ...state, agents });
}

export function setSelection(selected) {
  publish({ ...state, selected });
}
