/** Supported proxy agents shown in the UI and sent to the backend.
 *
 * Catalogue order, and it has to stay in step with AGENT_CATALOGUE in
 * backend/proxy/audit/agents.py: the backend allocates each agent's ports from
 * its position in that tuple, so the first entry here is the one on the port
 * the proxy has always listened on.
 */
export const AGENT_OPTIONS = ['AllTraffic', 'BrowserOS', 'MicrosoftEdge'];

/** The default selection: not a named agent, but everything pointed at the
 *  system proxy. */
export const ALL_TRAFFIC_AGENT = AGENT_OPTIONS[0];

const LISTEN_BASE = 8080;
const ADMIN_BASE = 8180;

export function defaultPortsForAgent(agentName) {
  const offset = AGENT_OPTIONS.indexOf(normalizeAgentName(agentName));
  if (offset < 0) return { proxyPort: null, adminPort: null };
  return { proxyPort: LISTEN_BASE + offset, adminPort: ADMIN_BASE + offset };
}

/** Display labels for ids that are not already readable. */
const AGENT_LABELS = {
  AllTraffic: 'All traffic',
};

/** Spellings that are not the canonical id — keep in sync with _ALIASES in
 *  backend/proxy/audit/agents.py */
const AGENT_ALIASES = {
  gemini: 'MicrosoftEdge',
  'all traffic': 'AllTraffic',
  'all-traffic': 'AllTraffic',
  all_traffic: 'AllTraffic',
};

function toCanonicalAgentName(trimmed) {
  const lower = trimmed.toLowerCase();
  const alias = AGENT_ALIASES[lower];
  if (alias) return alias;
  const canonical = AGENT_OPTIONS.find((name) => name.toLowerCase() === lower);
  return canonical ?? trimmed;
}

/** Maps stored / legacy values to canonical agent names for display and selection. */
export function normalizeAgentName(raw) {
  if (raw == null || String(raw).trim() === '') return '';
  return toCanonicalAgentName(String(raw).trim());
}

/** What a person reads. Unknown names are shown as recorded. */
export function agentLabel(raw) {
  const canonical = normalizeAgentName(raw);
  return AGENT_LABELS[canonical] ?? canonical;
}

export function resolveStoredAgent(stored) {
  const normalized = normalizeAgentName(stored);
  if (normalized && AGENT_OPTIONS.includes(normalized)) return normalized;
  return AGENT_OPTIONS[0];
}

/** Selection restored from storage, dropping names no longer in the catalogue
 *  and falling back to the default when nothing survives. */
export function resolveStoredAgents(stored) {
  const list = Array.isArray(stored) ? stored : [];
  const selected = AGENT_OPTIONS.filter((name) =>
    list.some((raw) => normalizeAgentName(raw) === name),
  );
  return selected.length > 0 ? selected : [ALL_TRAFFIC_AGENT];
}

/**
 * Settle a selection the person has just changed.
 *
 * All traffic and the named agents are two different ways of routing, not two
 * things to combine: All traffic is the system proxy, of which a machine has
 * exactly one, while a named agent is that one app launched at its own port.
 * Holding both at once would claim to be doing both, so whichever was just
 * picked wins and the other kind is dropped. Named agents still combine
 * freely with each other.
 */
export function reconcileAgentSelection(previous, next) {
  const before = resolveStoredAgents(previous);
  const after = AGENT_OPTIONS.filter((name) =>
    (Array.isArray(next) ? next : []).some((raw) => normalizeAgentName(raw) === name),
  );
  const added = after.filter((name) => !before.includes(name));

  if (added.includes(ALL_TRAFFIC_AGENT)) return [ALL_TRAFFIC_AGENT];
  if (added.length > 0) return after.filter((name) => name !== ALL_TRAFFIC_AGENT);
  // Nothing added, so this was a removal: never leave the selection empty.
  return after.length > 0 ? after : [ALL_TRAFFIC_AGENT];
}
