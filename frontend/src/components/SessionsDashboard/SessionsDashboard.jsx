import { useEffect, useMemo, useState } from 'react';
import './SessionsDashboard.css';

// TODO: Risk score thresholds (low, medium, high) are currently hardcoded for the mockup and should be configurable or driven by the backend in the future.
function getRiskLevel(score) {
  if (score > 0.7) return 'high';
  if (score > 0.4) return 'medium';
  return 'low';
}

/** Maps API session objects to the shape used by the table (list endpoint may omit some fields). */
function normalizeSession(api) {
  const avg = api.average_risk_score;
  const risk =
    typeof avg === 'number' && !Number.isNaN(avg) ? avg : 0;
  return {
    session_id: String(api.session_id),
    agent_name: api.agent_name ?? '',
    user:
      typeof api.user === 'string' && api.user.length > 0
        ? api.user
        : (api.environment ?? '—'),
    average_risk_score: risk,
    start_time: api.start_time,
    end_time: api.end_time,
  };
}

function formatIsoLocal(iso) {
  if (iso == null || iso === '') return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
}

async function readErrorMessage(response) {
  try {
    const body = await response.json();
    if (body && typeof body.error === 'string' && body.error) {
      return body.error;
    }
  } catch {
    /* ignore */
  }
  if (response.status === 401) {
    return 'You must be signed in to load sessions.';
  }
  if (response.status >= 500) {
    return 'The server had a problem. Please try again later.';
  }
  return `Could not load sessions (${response.status}).`;
}

function ShieldIcon() {
  return (
    <svg
      className="logo-shield-icon"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M9 12l2 2 4-4"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const AGENT_OPTIONS = ['Gemini', 'BrowserOS'];

function SessionsDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('Gemini');
  const [isProxyActive, setIsProxyActive] = useState(false);
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleProxyToggle = () => {
    setIsProxyActive((prev) => !prev);
  };

  const handleAgentSelect = (agent) => {
    if (agent !== selectedAgent) {
      setIsProxyActive(false);
    }
    setSelectedAgent(agent);
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
          setSessions(data.map(normalizeSession));
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
        session.user.toLowerCase().includes(query),
    );
  }, [searchTerm, sessions]);

  const showTable = !isLoading && !error;

  return (
    <div className="sessions-dashboard-root">
      <header className="sessions-dashboard-header">
        <div className="sessions-dashboard-brand">
          <ShieldIcon />
          <span>AgentGuard</span>
        </div>
        <nav className="sessions-dashboard-nav">
          <button className="nav-tab nav-tab--active">Sessions</button>
          <button className="nav-tab">Rules</button>
        </nav>
        <div className="sessions-dashboard-header-right">
          <div className="agent-selector">
            <span className="agent-selector-label">SELECT AGENT</span>
            <div className="agent-select-wrap">
              <button
                type="button"
                className="agent-select"
                onClick={() => setAgentDropdownOpen((open) => !open)}
                onBlur={() => setAgentDropdownOpen(false)}
                aria-haspopup="listbox"
                aria-expanded={agentDropdownOpen}
                aria-label="Select agent"
              >
                {selectedAgent}
              </button>
              {agentDropdownOpen && (
                <div className="agent-select-options" role="listbox">
                  {AGENT_OPTIONS.map((agent) => (
                    <button
                      key={agent}
                      type="button"
                      role="option"
                      aria-selected={selectedAgent === agent}
                      className={`agent-select-option ${selectedAgent === agent ? 'agent-select-option--active' : ''}`}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        handleAgentSelect(agent);
                      }}
                    >
                      {agent}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="sessions-dashboard-proxy">
            <span className="proxy-label">PROXY</span>
            <button
              type="button"
              className={`proxy-toggle ${isProxyActive ? 'proxy-toggle--on' : 'proxy-toggle--off'}`}
              onClick={handleProxyToggle}
              aria-pressed={isProxyActive}
              aria-label={`Toggle proxy for ${selectedAgent}`}
            >
              <span className="proxy-knob" />
            </button>
          </div>
        </div>
      </header>

      <main className="sessions-dashboard-main">
        <div className="sessions-dashboard-card">
          <div className="sessions-dashboard-card-header">
            <h1 className="sessions-title">Sessions Dashboard</h1>
            <input
              type="text"
              className="session-search-input"
              placeholder="Search Session..."
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
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
            <div className="sessions-table-wrapper">
              <table className="sessions-table">
                <thead>
                  <tr>
                    <th>AGENT NAME</th>
                    <th>SESSION ID</th>
                    <th>USER</th>
                    <th className="th-risk-center">AVERAGE RISK SCORE</th>
                    <th className="th-centered-block">START TIME</th>
                    <th className="th-centered-block">END TIME</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSessions.map((session) => {
                    const riskLevel = getRiskLevel(session.average_risk_score);
                    return (
                      <tr key={session.session_id} className="sessions-row">
                        <td className="cell-agent-name">{session.agent_name}</td>
                        <td className="cell-session-id">{session.session_id}</td>
                        <td className="cell-user">{session.user}</td>
                        <td className={`cell-risk cell-risk--${riskLevel} td-risk-center`}>
                          <span className="cell-risk-inner">
                            {session.average_risk_score.toFixed(2)}
                          </span>
                        </td>
                        <td className="cell-timestamp td-centered-block">
                          {formatIsoLocal(session.start_time)}
                        </td>
                        <td className="cell-timestamp td-centered-block">
                          {formatIsoLocal(session.end_time)}
                        </td>
                      </tr>
                    );
                  })}
                  {filteredSessions.length === 0 && sessions.length > 0 && (
                    <tr>
                      <td colSpan={6} className="sessions-empty-state">
                        No sessions match your search.
                      </td>
                    </tr>
                  )}
                  {sessions.length === 0 && (
                    <tr>
                      <td colSpan={6} className="sessions-empty-state">
                        No sessions yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default SessionsDashboard;
