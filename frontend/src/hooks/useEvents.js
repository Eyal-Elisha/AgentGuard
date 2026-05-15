import { useEffect, useMemo, useState } from 'react';
import { fetchWithBase, readErrorMessage } from '../components/SessionsDashboard/sessionUtils.js';
import { useSessionMeta } from './useSessionMeta.js';
import { useRuleAnalysis } from './useRuleAnalysis.js';

export function useEvents(sessionId) {
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const resolvedSessionId = useMemo(() => 
    typeof sessionId === 'string' && sessionId.startsWith(':') ? sessionId.slice(1) : sessionId
  , [sessionId]);

  const sessionMeta = useSessionMeta(resolvedSessionId);
  const ruleAnalysis = useRuleAnalysis(selectedEventId);

  useEffect(() => {
    let cancelled = false;
    async function loadEvents() {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetchWithBase(`/sessions/${resolvedSessionId}/events`);
        if (!res.ok) {
          const msg = await readErrorMessage(res);
          if (!cancelled) { setError(msg); setEvents([]); }
          return;
        }
        const data = await res.json();
        if (!cancelled) {
          setEvents(Array.isArray(data) ? data : []);
          if (data.length > 0) setSelectedEventId(data[0].event_id);
        }
      } catch {
        if (!cancelled) setError('Unable to reach the server.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    if (resolvedSessionId) loadEvents();
    return () => { cancelled = true; };
  }, [resolvedSessionId]);

  const selectedEvent = useMemo(() => 
    events.find((e) => e.event_id === selectedEventId) || null
  , [selectedEventId, events]);

  return {
    events,
    ruleAnalysis,
    selectedEventId,
    setSelectedEventId,
    sessionMeta,
    selectedEvent,
    isLoading,
    error,
    resolvedSessionId
  };
}
