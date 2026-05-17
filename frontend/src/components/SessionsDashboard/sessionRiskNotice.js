const SEEN_KEY = 'agentguard.seenSessionRiskNotices';

function readSeenIds() {
  try {
    return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || '[]'));
  } catch {
    return new Set();
  }
}

function writeSeenIds(ids) {
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify([...ids]));
  } catch {
    /* ignore storage failures */
  }
}

export function nextReviewSession(sessions) {
  const seen = readSeenIds();
  return sessions.find(
    (session) =>
      session.should_stop &&
      !session.end_time &&
      !seen.has(session.session_id),
  ) ?? null;
}

export function markReviewSessionSeen(sessionId) {
  const seen = readSeenIds();
  seen.add(String(sessionId));
  writeSeenIds(seen);
}

export function reviewSessionMessage(session) {
  return (
    `Session #${session.session_id} reached risk score ` +
    `${session.session_risk_score.toFixed(2)}. ` +
    'You should probably review it because this session is behaving unsafely.'
  );
}
