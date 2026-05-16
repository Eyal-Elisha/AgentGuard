/** Shown when a table cell has no value (user id, timestamps). En dash — longer than hyphen, same for all empty cells. */
export const EMPTY_CELL_DISPLAY = '–';

/**
 * Loads per-session risk summary from the backend.
 * Returns null if the request fails or the payload is invalid.
 * @param {Record<string, string>} [headers]
 */
export async function fetchSessionRiskStats(baseUrl, sessionId, headers) {
  const url = `${baseUrl}/sessions/${Number(sessionId)}/events/stats`;
  try {
    const response = await fetch(url, headers ? { headers } : undefined);
    if (!response.ok) return null;
    const data = await response.json();
    const score = data?.session_risk_score;
    if (typeof score === 'number' && !Number.isNaN(score)) return data;
    return { session_risk_score: 0 };
  } catch {
    return null;
  }
}

/** Maps API session objects to the shape used by the table (list endpoint may omit some fields). */
export function normalizeSession(sessionData) {
  const score = sessionData.session_risk_score ?? sessionData.average_risk_score;
  const risk =
    typeof score === 'number' && !Number.isNaN(score) ? score : 0;
  const rawUserId = sessionData.user_id;
  const user_id =
    typeof rawUserId === 'number' && Number.isFinite(rawUserId)
      ? rawUserId
      : null;
  return {
    session_id: String(sessionData.session_id),
    agent_name: sessionData.agent_name ?? '',
    user_id,
    session_risk_score: risk,
    risk_level: sessionData.risk_level ?? 'low',
    should_stop: Boolean(sessionData.should_stop),
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

/**
 * @param {Response} response
 * @param {string} [resourceLabel] noun phrase for errors, e.g. "sessions" or "rules"
 */
export async function readErrorMessage(response, resourceLabel = 'data') {
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
  return `Could not load ${resourceLabel} (${response.status}).`;
}
