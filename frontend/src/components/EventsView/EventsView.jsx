import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import SessionsDashboardHeader from '../SessionsDashboard/SessionsDashboardHeader.jsx';
import '../SessionsDashboard/SessionsDashboard.css';
import './EventsView.css';
import EventAnalysis from './EventAnalysis.jsx';
import EventTimeline from './EventTimeline.jsx';

const mockEvents = [
  {
    event_id: 5,
    timestamp: '2025-12-22 22:35:12',
    url: 'secure-login-bank.net/auth',
    guard_action: 'Block',
    risk_score: 0.92,
  },
  {
    event_id: 6,
    timestamp: '2025-12-22 22:32:45',
    url: 'api.currency-exchange.com/rates',
    guard_action: 'Warn',
    risk_score: 0.66,
  },
  {
    event_id: 7,
    timestamp: '2025-12-22 22:31:10',
    url: 'google.com/search?q=news',
    guard_action: 'Allow',
    risk_score: 0.12,
  },
];

const mockRuleAnalysis = [
  {
    analysis_id: 123,
    event_id: 5,
    rule_code: 'rule_typosquatting',
    rule_score: 1.0,
    details: "Domain 'secure-login-bank.net' mimics 'bank.com'",
  },
  {
    analysis_id: 124,
    event_id: 5,
    rule_code: 'rule_pii_transfer',
    rule_score: 0.85,
    details: 'Detected clear-text password pattern in POST body',
  },
];

function EventsView() {
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const resolvedSessionId =
    typeof sessionId === 'string' && sessionId.startsWith(':')
      ? sessionId.slice(1)
      : sessionId;
  const [selectedAgent, setSelectedAgent] = useState('Gemini');
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);
  const [isProxyActive, setIsProxyActive] = useState(true);
  const [selectedEventId, setSelectedEventId] = useState(mockEvents[0]?.event_id ?? null);

  const selectedEvent =
    mockEvents.find((event) => event.event_id === selectedEventId) ?? mockEvents[0] ?? null;

  const selectedEventRules = useMemo(() => {
    if (!selectedEvent) return [];
    return mockRuleAnalysis.filter((row) => row.event_id === selectedEvent.event_id);
  }, [selectedEvent]);

  const handleAgentSelect = (agent) => {
    if (agent !== selectedAgent) {
      setIsProxyActive(false);
    }
    setSelectedAgent(agent);
    setAgentDropdownOpen(false);
  };

  return (
    <div className="sessions-dashboard-root events-view-root">
      <SessionsDashboardHeader
        selectedAgent={selectedAgent}
        agentDropdownOpen={agentDropdownOpen}
        onToggleAgentDropdown={() => setAgentDropdownOpen((open) => !open)}
        onCloseAgentDropdown={() => setAgentDropdownOpen(false)}
        onAgentSelect={handleAgentSelect}
        isProxyActive={isProxyActive}
        onProxyToggle={() => setIsProxyActive((prev) => !prev)}
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

          <div className="events-view-grid">
            <EventTimeline
              events={mockEvents}
              selectedEventId={selectedEvent?.event_id ?? null}
              onSelectEvent={setSelectedEventId}
            />
            <EventAnalysis
              selectedEvent={selectedEvent}
              ruleAnalysisRows={selectedEventRules}
            />
          </div>
        </section>
      </main>
    </div>
  );
}

export default EventsView;
