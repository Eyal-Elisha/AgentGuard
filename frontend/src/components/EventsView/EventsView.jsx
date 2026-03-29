import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import SessionsDashboardHeader from '../SessionsDashboard/SessionsDashboardHeader.jsx';
import '../SessionsDashboard/SessionsDashboard.css';
import './EventsView.css';
import EventAnalysis from './EventAnalysis.jsx';
import EventTimeline from './EventTimeline.jsx';
import { readErrorMessage } from '../SessionsDashboard/sessionUtils.js';

function EventsView({ selectedAgent, onAgentSelect, isProxyActive, onProxyToggle }) {
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const resolvedSessionId =
    typeof sessionId === 'string' && sessionId.startsWith(':')
      ? sessionId.slice(1)
      : sessionId;
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);

  const [events, setEvents] = useState([]);
  const [ruleAnalysis, setRuleAnalysis] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch Session Events
  useEffect(() => {
    let cancelled = false;

    async function loadEvents() {
      setIsLoading(true);
      setError(null);
      const base = import.meta.env.VITE_API_BASE_URL;
      
      if (!base) {
        if (!cancelled) {
          setError('API base URL is not configured. Set VITE_API_BASE_URL in your .env file.');
          setIsLoading(false);
        }
        return;
      }

      const baseUrl = String(base).replace(/\/$/, '');
      const url = `${baseUrl}/sessions/${resolvedSessionId}/events`;

      try {
        const response = await fetch(url);

        if (!response.ok) {
          const message = await readErrorMessage(response);
          if (!cancelled) {
            setEvents([]);
            setError(message);
          }
          return;
        }

        const data = await response.json();
        if (!Array.isArray(data)) {
          if (!cancelled) {
            setEvents([]);
            setError('Received an unexpected response from the server.');
          }
          return;
        }

        if (!cancelled) {
          setEvents(data);
          if (data.length > 0) {
            setSelectedEventId(data[0].event_id);
          } else {
            setSelectedEventId(null);
            setRuleAnalysis([]);
          }
        }
      } catch {
        if (!cancelled) {
          setEvents([]);
          setError(
            'Unable to reach the server. Check your connection and that the API is running.',
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    if (resolvedSessionId) {
      loadEvents();
    }
    
    return () => {
      cancelled = true;
    };
  }, [resolvedSessionId]);

  // Fetch Rule Analysis for selectedEventId
  useEffect(() => {
    let cancelled = false;

    async function loadRuleAnalysis() {
      if (!selectedEventId) {
        if (!cancelled) setRuleAnalysis([]);
        return;
      }
      
      const base = import.meta.env.VITE_API_BASE_URL;
      if (!base) return;
      const baseUrl = String(base).replace(/\/$/, '');
      const url = `${baseUrl}/events/${selectedEventId}/rules-analysis`;

      try {
        const response = await fetch(url);
        if (!response.ok) {
          if (!cancelled) setRuleAnalysis([]);
          return;
        }
        const data = await response.json();
        if (!cancelled) {
          setRuleAnalysis(Array.isArray(data) ? data : []);
        }
      } catch {
        if (!cancelled) setRuleAnalysis([]);
      }
    }

    loadRuleAnalysis();
    
    return () => {
      cancelled = true;
    };
  }, [selectedEventId]);

  const selectedEvent = useMemo(() => {
    if (!selectedEventId || !events) return null;
    return events.find((e) => e.event_id === selectedEventId) ?? null;
  }, [selectedEventId, events]);

  const handleAgentSelectLocal = (agent) => {
    onAgentSelect(agent);
    setAgentDropdownOpen(false);
  };

  return (
    <div className="sessions-dashboard-root events-view-root">
      <SessionsDashboardHeader
        selectedAgent={selectedAgent}
        agentDropdownOpen={agentDropdownOpen}
        onToggleAgentDropdown={() => setAgentDropdownOpen((open) => !open)}
        onCloseAgentDropdown={() => setAgentDropdownOpen(false)}
        onAgentSelect={handleAgentSelectLocal}
        isProxyActive={isProxyActive}
        onProxyToggle={onProxyToggle}
      />

      <main className="sessions-dashboard-main events-view-main">
        <section className="sessions-dashboard-card events-view-card">
          <div className="events-view-title-area">
            <button
              type="button"
              className="events-view-back-button"
              onClick={() => navigate('/')}
            >
              <span aria-hidden="true">←</span>
              <span>Back to Sessions</span>
            </button>
            <h1 className="events-view-title">
              Agent: <span>{selectedAgent}</span>
            </h1>
            <p className="events-view-subtitle">
              Session Events: <strong>{resolvedSessionId ?? 'SESS-7729'}</strong>
              <span className="events-view-subtitle-sep">User:</span>
              <strong>test</strong>
            </p>
          </div>

          {isLoading && (
            <div className="sessions-loading" role="status" aria-live="polite">
              Loading events...
            </div>
          )}

          {error && (
            <div className="sessions-error-alert" role="alert">
              {error}
            </div>
          )}

          {!isLoading && !error && events.length === 0 && (
            <div className="sessions-empty-state">
              No events recorded for this session.
            </div>
          )}

          {!isLoading && !error && events.length > 0 && (
            <div className="events-view-grid">
              <EventTimeline
                events={events}
                selectedEventId={selectedEventId}
                onSelectEvent={setSelectedEventId}
              />
              <EventAnalysis
                selectedEvent={selectedEvent}
                ruleAnalysisRows={ruleAnalysis}
              />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default EventsView;
