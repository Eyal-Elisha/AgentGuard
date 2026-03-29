/** Shown when a table cell has no value (user id, timestamps). En dash — longer than hyphen, same for all empty cells. */
export const EMPTY_CELL_DISPLAY = '–';

/**
 * Loads per-session aggregates from the backend (list `/sessions` does not include average risk).
 * Returns null if the request fails or the payload is invalid.
 */
export async function fetchSessionEventStats(baseUrl, sessionId) {
  const url = `${baseUrl}/sessions/${Number(sessionId)}/events/stats`;
  try {
    const response = await fetch(url);
    if (!response.ok) return null;
    const data = await response.json();
    const avg = data?.average_risk_score;
    if (typeof avg === 'number' && !Number.isNaN(avg)) return avg;
    return 0;
  } catch {
    return null;
  }
}

/** Maps API session objects to the shape used by the table (list endpoint may omit some fields). */
export function normalizeSession(sessionData) {
  const avg = sessionData.average_risk_score;
  const risk =
    typeof avg === 'number' && !Number.isNaN(avg) ? avg : 0;
  const rawUserId = sessionData.user_id;
  const user_id =
    typeof rawUserId === 'number' && Number.isFinite(rawUserId)
      ? rawUserId
      : null;
  return {
    session_id: String(sessionData.session_id),
    agent_name: sessionData.agent_name ?? '',
    user_id,
    average_risk_score: risk,
    start_time: sessionData.start_time,
    end_time: sessionData.end_time,
  };
}

/** True when `formatIsoLocal` would show {@link EMPTY_CELL_DISPLAY} instead of a formatted time. */
export function isIsoEmpty(iso) {
  if (iso == null || iso === '') return true;
  const d = new Date(iso);
  return Number.isNaN(d.getTime());
}

export function formatIsoLocal(iso) {
  if (isIsoEmpty(iso)) return EMPTY_CELL_DISPLAY;
  return new Date(iso).toLocaleString();
}

export async function readErrorMessage(response) {
  try {
    const body = await response.json();
    if (body && typeof body.error === 'string' && body.error) {
      return body.error;
    }
  } catch {
    /* ignore */
  }
  if (response.status >= 500) {
    return 'The server had a problem. Please try again later.';
  }
  return `Could not load sessions (${response.status}).`;
}
