/** Shown when a table cell has no value (user id, timestamps). */
export const EMPTY_CELL_DISPLAY = '–';

/** Utility to get risk level string from score */
export function getRiskLevel(score) {
  if (typeof score !== 'number' || Number.isNaN(score)) return 'low';
  if (score > 0.7) return 'high';
  if (score > 0.4) return 'medium';
  return 'low';
}

/** Get API base URL from env */
export function getApiBase() {
  const base = import.meta.env.VITE_API_BASE_URL;
  if (!base) return null;
  return String(base).replace(/\/$/, '');
}

import { getToken } from '../../api/authToken.js';

/** Helper for fetching from API with base URL */
export async function fetchWithBase(path, options = {}) {
  const base = getApiBase();
  if (!base) throw new Error('API base URL not configured');
  
  const token = getToken();
  const headers = { ...options.headers };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return fetch(`${base}${path}`, { ...options, headers });
}

/** Loads per-session aggregates from the backend. */
export async function fetchSessionEventStats(baseUrl, sessionId, headers) {
  try {
    const response = await fetchWithBase(`/sessions/${Number(sessionId)}/events/stats`, headers ? { headers } : undefined);
    if (!response.ok) return null;
    const data = await response.json();
    const avg = data?.average_risk_score;
    return typeof avg === 'number' && !Number.isNaN(avg) ? avg : 0;
  } catch {
    return null;
  }
}

/** Maps API session objects to the shape used by the table. */
export function normalizeSession(sessionData) {
  const avg = sessionData.average_risk_score;
  const risk = typeof avg === 'number' && !Number.isNaN(avg) ? avg : 0;
  const rawUserId = sessionData.user_id;
  const user_id = typeof rawUserId === 'number' && Number.isFinite(rawUserId) ? rawUserId : null;
  
  return {
    session_id: String(sessionData.session_id),
    agent_name: sessionData.agent_name ?? '',
    user_id,
    average_risk_score: risk,
    start_time: sessionData.start_time,
    end_time: sessionData.end_time,
  };
}

export function isIsoEmpty(iso) {
  if (iso == null || iso === '') return true;
  const d = new Date(iso);
  return Number.isNaN(d.getTime());
}

export function formatIsoLocal(iso) {
  if (isIsoEmpty(iso)) return EMPTY_CELL_DISPLAY;
  return new Date(iso).toLocaleString();
}

/** Read error message from response body or status */
export async function readErrorMessage(response, resourceLabel = 'data') {
  try {
    const body = await response.json();
    if (body?.error) return body.error;
  } catch { /* ignore */ }
  
  if (response.status >= 500) return 'The server had a problem. Please try again later.';
  return `Could not load ${resourceLabel} (${response.status}).`;
}
