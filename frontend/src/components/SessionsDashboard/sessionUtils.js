/** Maps API session objects to the shape used by the table (list endpoint may omit some fields). */
export function normalizeSession(sessionData) {
  const avg = sessionData.average_risk_score;
  const risk =
    typeof avg === 'number' && !Number.isNaN(avg) ? avg : 0;
  const rawUserId = sessionData.user_id;
  const user_id =
    rawUserId != null && rawUserId !== '' ? String(rawUserId) : 'test';
  return {
    session_id: String(sessionData.session_id),
    agent_name: sessionData.agent_name ?? '',
    user_id,
    average_risk_score: risk,
    start_time: sessionData.start_time,
    end_time: sessionData.end_time,
  };
}

export function formatIsoLocal(iso) {
  if (iso == null || iso === '') return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
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
