import { useEffect, useState } from 'react';
import { fetchWithBase, readErrorMessage } from '../components/SessionsDashboard/sessionUtils.js';

export function useAdminStats() {
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function loadStats() {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetchWithBase('/admin/stats');
        if (!res.ok) {
          const msg = await readErrorMessage(res, 'admin stats');
          if (!cancelled) { setError(msg); setStats(null); }
          return;
        }
        const data = await res.json();
        if (!cancelled) {
          setStats(data);
        }
      } catch {
        if (!cancelled) setError('Unable to reach the server.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    loadStats();
    return () => { cancelled = true; };
  }, []);

  return { stats, isLoading, error };
}
