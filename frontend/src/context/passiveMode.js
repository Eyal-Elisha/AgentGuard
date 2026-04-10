import { fetchPassiveMode, patchPassiveMode } from '../api/proxy/passiveMode.js';

const STORAGE_KEY = 'agentguard-passive-mode';

// ============================================================================
// Module-level state store with subscriptions (required by useSyncExternalStore)
// ============================================================================

let state = localStorage.getItem(STORAGE_KEY) === '1';
const subscribers = new Set();

function notifySubscribers() {
  subscribers.forEach((fn) => fn());
}

// ============================================================================
// Public API
// ============================================================================

export function subscribe(callback) {
  subscribers.add(callback);
  return () => subscribers.delete(callback);
}

export function getSnapshot() {
  return state;
}

export async function syncFromServer() {
  const serverValue = await fetchPassiveMode();
  setState(serverValue);
}

export async function toggle() {
  const next = !state;
  setState(next);
  try {
    const confirmed = await patchPassiveMode(next);
    setState(confirmed);
  } catch (_) {
    setState(!next); // rollback on error
  }
}

// ============================================================================
// Private helpers
// ============================================================================

function setState(value) {
  if (value === state) return;
  state = value;
  localStorage.setItem(STORAGE_KEY, value ? '1' : '0');
  notifySubscribers();
}
