import { useEffect, useMemo, useState } from 'react';
import SessionSearchBar from './SessionSearchBar.jsx';
import SessionsDashboardHeader from './SessionsDashboardHeader.jsx';
import SessionsTable from './SessionsTable.jsx';
import {
  fetchSessionEventStats,
  normalizeSession,
  readErrorMessage,
} from './sessionUtils.js';
import './SessionsDashboard.css';

function SessionsDashboard({ selectedAgent, onAgentSelect, isProxyActive, onProxyToggle }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleAgentSelectLocal = (agent) => {
    onAgentSelect(agent);
    setAgentDropdownOpen(false);
  };

  useEffect(() => {
    let cancelled = false;

    async function loadSessions() {
      const base = import.meta.env.VITE_API_BASE_URL;
      if (base == null || String(base).trim() === '') {
        if (!cancelled) {
          setError('API base URL is not configured. Set VITE_API_BASE_URL in your .env file.');
          setIsLoading(false);
        }
        return;
      }

      const baseUrl = String(base).replace(/\/$/, '');
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
              const avg = await fetchSessionEventStats(
                baseUrl,
                raw.session_id,
              );
              return normalizeSession({
                ...raw,
                average_risk_score:
                  avg !== null ? avg : raw.average_risk_score,
              });
            }),
          );
          setSessions(merged);
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
  }, []);

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
    <div className="sessions-dashboard-root">
      <SessionsDashboardHeader
        selectedAgent={selectedAgent}
        agentDropdownOpen={agentDropdownOpen}
        onToggleAgentDropdown={() =>
          setAgentDropdownOpen((open) => !open)
        }
        onCloseAgentDropdown={() => setAgentDropdownOpen(false)}
        onAgentSelect={handleAgentSelectLocal}
        isProxyActive={isProxyActive}
        onProxyToggle={onProxyToggle}
      />

      <main className="sessions-dashboard-main">
        <div className="sessions-dashboard-card">
          <SessionSearchBar
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            disabled={!showTable}
          />

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
            <SessionsTable
              filteredSessions={filteredSessions}
              sessions={sessions}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default SessionsDashboard;
