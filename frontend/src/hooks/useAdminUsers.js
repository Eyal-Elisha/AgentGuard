import { useEffect, useState } from 'react';
import { fetchWithBase, readErrorMessage } from '../components/SessionsDashboard/sessionUtils.js';

export function useAdminUsers(enabled = true) {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!enabled) {
      setUsers([]);
      setIsLoading(false);
      setError(null);
      return;
    }
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
  }, [enabled]);

  async function promoteToAdmin(userId) {
    try {
      const res = await fetchWithBase(`/users/${userId}/admin`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_admin: true }),
      });
      if (!res.ok) {
        return await readErrorMessage(res, 'user');
      }
      setUsers((prev) => prev.map((u) => (u.user_id === userId ? { ...u, is_admin: true } : u)));
      return null;
    } catch {
      return 'Unable to reach the server.';
    }
  }

  return { users, isLoading, error, promoteToAdmin };
}
