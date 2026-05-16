import { useEffect, useState } from 'react';
import { fetchWithBase, readErrorMessage } from '../components/SessionsDashboard/sessionUtils.js';

export function useAdminUsers() {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function loadUsers() {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetchWithBase('/users');
        if (!res.ok) {
          const msg = await readErrorMessage(res, 'users');
          if (!cancelled) { setError(msg); setUsers([]); }
          return;
        }
        const data = await res.json();
        if (!cancelled) {
          setUsers(Array.isArray(data) ? data : []);
        }
      } catch {
        if (!cancelled) setError('Unable to reach the server.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    loadUsers();
    return () => { cancelled = true; };
  }, []);

  return { users, isLoading, error };
}
