import { useEffect, useState } from 'react';
import { fetchSessionEventStats, fetchWithBase } from '../components/SessionsDashboard/sessionUtils.js';

export function useSessionMeta(resolvedSessionId) {
  const [sessionMeta, setSessionMeta] = useState({ avgScore: null, userId: null, username: null });

  useEffect(() => {
    let cancelled = false;
    async function loadMeta() {
      try {
        const baseUrl = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
        const [res, avg] = await Promise.all([
          fetchWithBase(`/sessions/${Number(resolvedSessionId)}`),
          fetchSessionEventStats(baseUrl, resolvedSessionId)
        ]);
        
        let meta = { avgScore: avg, userId: null, username: null };
        if (res.ok) {
          const data = await res.json();
          meta.userId = typeof data?.user_id === 'number' ? data.user_id : null;
          if (meta.userId != null) {
            const uRes = await fetchWithBase(`/users/${meta.userId}`);
            if (uRes.ok) {
              const uData = await uRes.json();
              meta.username = uData?.username || null;
            }
          }
        }
        if (!cancelled) setSessionMeta(meta);
      } catch { /* ignore */ }
    }
    if (resolvedSessionId) loadMeta();
    return () => { cancelled = true; };
  }, [resolvedSessionId]);

  return sessionMeta;
}
