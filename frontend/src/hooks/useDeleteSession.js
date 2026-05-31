import { useState } from 'react';
import { fetchWithBase } from '../components/SessionsDashboard/sessionUtils.js';

/**
 * Provides a deleteSession function that calls DELETE /sessions/:id.
 * Calls onSuccess() after a successful deletion so the parent can refresh.
 */
export function useDeleteSession(onSuccess) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState(null);

  async function deleteSession(sessionId) {
    setIsPending(true);
    setError(null);
    try {
      const res = await fetchWithBase(`/sessions/${sessionId}`, { method: 'DELETE' });
      if (!res.ok) {
        let msg = `Failed to delete session (${res.status}).`;
        try {
          const body = await res.json();
          if (body?.error) msg = body.error;
        } catch { /* ignore */ }
        setError(msg);
        return false;
      }
      onSuccess?.(sessionId);
      return true;
    } catch {
      setError('Unable to reach the server.');
      return false;
    } finally {
      setIsPending(false);
    }
  }

  return { deleteSession, isPending, error };
}
