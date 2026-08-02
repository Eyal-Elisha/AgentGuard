const STORAGE_PREFIX = 'agentguard-tour-v1:';

export function userKeyFrom(user) {
  if (!user) return 'anonymous';
  return String(user.userId ?? user.username ?? 'anonymous');
}

export function tourStorageKey(userKey) {
  return `${STORAGE_PREFIX}${userKey || 'anonymous'}`;
}

export function isTourCompleted(userKey) {
  try {
    return window.localStorage.getItem(tourStorageKey(userKey)) === '1';
  } catch {
    return false;
  }
}

export function setTourCompleted(userKey, completed = true) {
  try {
    const key = tourStorageKey(userKey);
    if (completed) window.localStorage.setItem(key, '1');
    else window.localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}
