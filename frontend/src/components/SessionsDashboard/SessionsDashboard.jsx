import { useEffect, useMemo, useState } from 'react';
import SessionRiskNotice from './SessionRiskNotice.jsx';
import SessionSearchBar from './SessionSearchBar.jsx';
import SessionsTable from './SessionsTable.jsx';
import { nextReviewSession } from './sessionRiskNotice.js';
import {
  fetchSessionRiskStats,
  normalizeSession,
  readErrorMessage,
} from './sessionUtils.js';
import './SessionsDashboard.css';

function SessionsDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [sessions, setSessions] = useState([]);
  const [riskNoticeSession, setRiskNoticeSession] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const base = import.meta.env.VITE_API_BASE_URL;
  const baseUrl =
    base == null || String(base).trim() === ''
      ? null
      : String(base).replace(/\/$/, '');

  useEffect(() => {
    let cancelled = false;

    async function loadSessions() {
      if (!baseUrl) {
        if (!cancelled) {
          setError('API base URL is not configured. Set VITE_API_BASE_URL in your .env file.');
          setIsLoading(false);
        }
        return;
      }

      const url = `${baseUrl}/sessions`;

      try {
        const response = await fetch(url);

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
              const riskStats = await fetchSessionRiskStats(
                baseUrl,
                raw.session_id,
              );
              return normalizeSession({
                ...raw,
                ...(riskStats ?? {}),
              });
            }),
          );
          setSessions(merged);
          setRiskNoticeSession(nextReviewSession(merged));
          setError(null);
        }
      } catch {
        if (!cancelled) {
          setSessions([]);
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

    loadSessions();
    return () => {
      cancelled = true;
    };
  }, [baseUrl]);

  const filteredSessions = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return sessions;
    return sessions.filter(
      (session) =>
        session.agent_name.toLowerCase().includes(query) ||
        session.session_id.toLowerCase().includes(query) ||
        (session.user_id != null &&
          String(session.user_id).includes(query)),
    );
  }, [searchTerm, sessions]);

  const showTable = !isLoading && !error;

  return (
    <div className="sessions-page">
      <main className="sessions-dashboard-main">
        <div className="sessions-dashboard-card">
          <div className="sessions-dashboard-card-header">
            <h1 className="sessions-title">Sessions</h1>
            <SessionSearchBar
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              disabled={!showTable}
            />
          </div>

          {isLoading && (
            <div className="sessions-loading" role="status" aria-live="polite">
              Loading sessions...
            </div>
          )}

          {error && (
            <div className="sessions-error-alert" role="alert">
              {error}
            </div>
          )}

          {showTable && (
            <>
              <SessionsTable
                filteredSessions={filteredSessions}
                sessions={sessions}
              />
              <SessionRiskNotice
                session={riskNoticeSession}
                onClose={() => setRiskNoticeSession(null)}
              />
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default SessionsDashboard;
