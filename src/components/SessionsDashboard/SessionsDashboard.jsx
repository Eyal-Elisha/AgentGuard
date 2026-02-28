import { useMemo, useState } from 'react';
import './SessionsDashboard.css';

const MOCK_SESSIONS = [
  {
    session_id: 'SESS-7729',
    agent_name: 'Gemini',
    user: 'John Doe',
    average_risk_score: 0.92,
    start_time: '2025-12-22T22:30:15Z',
    end_time: '2025-12-22T22:45:00Z',
  },
  {
    session_id: 'SESS-8104',
    agent_name: 'BrowserOS',
    user: 'Alex Smith',
    average_risk_score: 0.55,
    start_time: '2025-12-22T21:10:04Z',
    end_time: '2025-12-22T21:55:20Z',
  },
  {
    session_id: 'SESS-6901',
    agent_name: 'Gemini',
    user: 'Sam Taylor',
    average_risk_score: 0.21,
    start_time: '2025-12-22T20:01:10Z',
    end_time: '2025-12-22T20:30:42Z',
  },
];

// TODO: Risk score thresholds (low, medium, high) are currently hardcoded for the mockup and should be configurable or driven by the backend in the future.
function getRiskLevel(score) {
  if (score > 0.7) return 'high';
  if (score > 0.4) return 'medium';
  return 'low';
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

  const filteredSessions = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return MOCK_SESSIONS;
    return MOCK_SESSIONS.filter(
      (session) =>
        session.agent_name.toLowerCase().includes(query) ||
        session.session_id.toLowerCase().includes(query) ||
        session.user.toLowerCase().includes(query),
    );
  }, [searchTerm]);

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
            />
          </div>

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
                        {new Date(session.start_time).toLocaleString()}
                      </td>
                      <td className="cell-timestamp td-centered-block">
                        {new Date(session.end_time).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
                {filteredSessions.length === 0 && (
                  <tr>
                    <td colSpan={6} className="sessions-empty-state">
                      No sessions match your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}

export default SessionsDashboard;

