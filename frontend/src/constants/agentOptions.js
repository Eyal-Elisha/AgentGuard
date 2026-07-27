/** Supported proxy agents shown in the UI and sent to the backend. */
export const AGENT_OPTIONS = ['MicrosoftEdge', 'BrowserOS'];

/** Renamed agents only — keep in sync with _LEGACY_AGENT_ALIASES in backend/proxy/audit.py */
const LEGACY_AGENT_KEYS = {
  gemini: 'MicrosoftEdge',
};

function toCanonicalAgentName(trimmed) {
  const legacy = LEGACY_AGENT_KEYS[trimmed.toLowerCase()];
  if (legacy) return legacy;
  const lower = trimmed.toLowerCase();
  const canonical = AGENT_OPTIONS.find((name) => name.toLowerCase() === lower);
  return canonical ?? trimmed;
}

/** Maps stored / legacy values to canonical agent names for display and selection. */
export function normalizeAgentName(raw) {
  if (raw == null || String(raw).trim() === '') return '';
  return toCanonicalAgentName(String(raw).trim());
}

export function resolveStoredAgent(stored) {
  const normalized = normalizeAgentName(stored);
  if (normalized && AGENT_OPTIONS.includes(normalized)) return normalized;
  return AGENT_OPTIONS[0];
}
