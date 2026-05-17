import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAgent } from '../../context/AgentContext.jsx';
import '../SessionsDashboard/SessionsDashboard.css';
import './EventsView.css';
import EventAnalysis from './EventAnalysis.jsx';
import EventTimeline from './EventTimeline.jsx';
import SessionReviewBanner from './SessionReviewBanner.jsx';
import { EMPTY_CELL_DISPLAY, fetchSessionRiskStats, readErrorMessage } from '../SessionsDashboard/sessionUtils.js';

function EventsView() {
  const navigate = useNavigate();
  const { selectedAgent } = useAgent();
  const { sessionId } = useParams();
  const resolvedSessionId =
    typeof sessionId === 'string' && sessionId.startsWith(':')
      ? sessionId.slice(1)
      : sessionId;

  const [events, setEvents] = useState([]);
  const [ruleAnalysis, setRuleAnalysis] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [sessionRiskScore, setSessionRiskScore] = useState(null);
  const [sessionRisk, setSessionRisk] = useState(null);
  const [sessionUserId, setSessionUserId] = useState(null);
  const [sessionUsername, setSessionUsername] = useState(null);
  const [sessionEndTime, setSessionEndTime] = useState(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const base = import.meta.env.VITE_API_BASE_URL;
  const baseUrl =
    base == null || String(base).trim() === ''
      ? null
      : String(base).replace(/\/$/, '');

  function getRiskLevel(score) {
    if (typeof score !== 'number' || Number.isNaN(score)) return 'low';
    if (score >= 0.93) return 'critical';
    if (score >= 0.9) return 'high';
    if (score >= 0.75) return 'medium';
    return 'low';
  }

  // Fetch Session Events
  useEffect(() => {
    let cancelled = false;

    async function loadEvents() {
      setIsLoading(true);
      setError(null);
      if (!baseUrl) {
        if (!cancelled) {
          setError('API base URL is not configured. Set VITE_API_BASE_URL in your .env file.');
          setIsLoading(false);
        }
        return;
      }

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
  }, [baseUrl, resolvedSessionId]);

  // Fetch Session metadata (user_id)
  useEffect(() => {
    let cancelled = false;

    async function loadSessionMeta() {
      if (!baseUrl || !resolvedSessionId) {
        if (!cancelled) setSessionUserId(null);
        if (!cancelled) setSessionUsername(null);
        if (!cancelled) setSessionEndTime(null);
        return;
      }
      const url = `${baseUrl}/sessions/${Number(resolvedSessionId)}`;
      try {
        const response = await fetch(url);
        if (!response.ok) {
          if (!cancelled) setSessionUserId(null);
          if (!cancelled) setSessionUsername(null);
          if (!cancelled) setSessionEndTime(null);
          return;
        }
        const data = await response.json();
        if (!cancelled) setSessionEndTime(data?.end_time ?? null);
        const rawUserId = data?.user_id;
        const user_id =
          typeof rawUserId === 'number' && Number.isFinite(rawUserId)
            ? rawUserId
            : null;
        if (!cancelled) setSessionUserId(user_id);

        if (user_id == null) {
          if (!cancelled) setSessionUsername(null);
          return;
        }

        const userUrl = `${baseUrl}/users/${user_id}`;
        const userRes = await fetch(userUrl);
        if (!userRes.ok) {
          if (!cancelled) setSessionUsername(null);
          return;
        }
        const userData = await userRes.json();
        const username = typeof userData?.username === 'string' ? userData.username : null;
        if (!cancelled) setSessionUsername(username);
      } catch {
        if (!cancelled) setSessionUserId(null);
        if (!cancelled) setSessionUsername(null);
        if (!cancelled) setSessionEndTime(null);
      }
    }

    loadSessionMeta();
    return () => {
      cancelled = true;
    };
  }, [baseUrl, resolvedSessionId]);

  // Fetch Session Risk Score
  useEffect(() => {
    let cancelled = false;

    async function loadSessionRiskScore() {
      if (!baseUrl || !resolvedSessionId) {
        if (!cancelled) setSessionRiskScore(null);
        if (!cancelled) setSessionRisk(null);
        return;
      }
      const riskStats = await fetchSessionRiskStats(baseUrl, resolvedSessionId);
      if (!cancelled) {
        setSessionRiskScore(riskStats?.session_risk_score ?? null);
        setSessionRisk(
          riskStats ? { ...riskStats, session_id: String(resolvedSessionId) } : null,
        );
      }
    }

    loadSessionRiskScore();

    return () => {
      cancelled = true;
    };
  }, [baseUrl, resolvedSessionId]);

  // Fetch Rule Analysis for selectedEventId
  useEffect(() => {
    let cancelled = false;

    async function loadRuleAnalysis() {
      if (!selectedEventId) {
        if (!cancelled) setRuleAnalysis([]);
        return;
      }
      
      if (!baseUrl) return;
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
  }, [baseUrl, selectedEventId]);

  const selectedEvent = useMemo(() => {
    if (!selectedEventId || !events) return null;
    return events.find((e) => e.event_id === selectedEventId) ?? null;
  }, [selectedEventId, events]);

  const sessionAvgRiskLevel = useMemo(
    () => getRiskLevel(sessionRiskScore),
    [sessionRiskScore],
  );

  return (
    <div className="sessions-page events-view-root">
      <main className="sessions-dashboard-main events-view-main">
        <section className="sessions-dashboard-card events-view-card">
          <div className="events-view-title-area">
            <button
              type="button"
              className="events-view-back-button"
              onClick={() => navigate('/sessions')}
            >
              <span aria-hidden="true">←</span>
              <span>Back to Sessions</span>
            </button>
            <h1 className="events-view-title">
              <span className="events-view-title-left">
                Agent: <span>{selectedAgent}</span>
              </span>
              <span className="events-view-title-metric">
                <span className="events-view-title-metric-label">Session Risk Score:</span>
                <span
                  className={`cell-risk cell-risk--${sessionAvgRiskLevel} events-view-title-metric-value`}
                >
                  {typeof sessionRiskScore === 'number'
                    ? sessionRiskScore.toFixed(2)
                    : '–'}
                </span>
              </span>
            </h1>
            <p className="events-view-subtitle">
              Session ID: <strong>{resolvedSessionId ?? 'SESS-7729'}</strong>
              <span className="events-view-subtitle-sep">User ID:</span>
              <strong>{sessionUserId == null ? EMPTY_CELL_DISPLAY : sessionUserId}</strong>
              <span className="events-view-subtitle-sep">Username:</span>
              <strong>{sessionUsername == null ? EMPTY_CELL_DISPLAY : sessionUsername}</strong>
            </p>
          </div>

          <SessionReviewBanner sessionRisk={sessionRisk} />

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
