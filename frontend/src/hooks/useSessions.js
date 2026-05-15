import { useEffect, useMemo, useState } from 'react';
import {
  fetchSessionEventStats,
  getApiBase,
  normalizeSession,
  readErrorMessage,
} from '../components/SessionsDashboard/sessionUtils.js';

export function useSessions(searchTerm) {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSessions() {
      const baseUrl = getApiBase();
      if (!baseUrl) {
        if (!cancelled) {
          setError('API base URL is not configured.');
          setIsLoading(false);
        }
        return;
      }

      try {
        const response = await fetch(`${baseUrl}/sessions`);
        if (!response.ok) {
          const message = await readErrorMessage(response);
          if (!cancelled) {
            setSessions([]);
            setError(message);
          }
          return;
        }

        const data = await response.json();
        if (!Array.isArray(data)) {
          if (!cancelled) {
            setSessions([]);
            setError('Received an unexpected response from the server.');
          }
          return;
        }

        if (!cancelled) {
          const merged = await Promise.all(
            data.map(async (raw) => {
              const avg = await fetchSessionEventStats(baseUrl, raw.session_id);
              return normalizeSession({
                ...raw,
                average_risk_score: avg !== null ? avg : raw.average_risk_score,
              });
            })
          );
          setSessions(merged);
          setError(null);
        }
      } catch {
        if (!cancelled) {
          setSessions([]);
          setError('Unable to reach the server.');
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadSessions();
    return () => { cancelled = true; };
  }, []);

  const filteredSessions = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return sessions;
    return sessions.filter(
      (s) =>
        s.agent_name.toLowerCase().includes(query) ||
        s.session_id.toLowerCase().includes(query) ||
        (s.user_id != null && String(s.user_id).includes(query))
    );
  }, [searchTerm, sessions]);

  return { filteredSessions, sessions, isLoading, error };
}
