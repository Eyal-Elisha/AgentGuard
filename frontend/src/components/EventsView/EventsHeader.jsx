import { useNavigate } from 'react-router-dom';
import { useAgent } from '../../context/AgentContext.jsx';
import { EMPTY_CELL_DISPLAY, getRiskLevel } from '../SessionsDashboard/sessionUtils.js';

export default function EventsHeader({ sessionId, meta }) {
  const navigate = useNavigate();
  const { selectedAgent } = useAgent();
  const riskLevel = getRiskLevel(meta.avgScore);

  return (
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
          <span className="events-view-title-metric-label">Average Risk Score:</span>
          <span className={`cell-risk cell-risk--${riskLevel} events-view-title-metric-value`}>
            {typeof meta.avgScore === 'number' ? meta.avgScore.toFixed(2) : '–'}
          </span>
        </span>
      </h1>
      <p className="events-view-subtitle">
        Session ID: <strong>{sessionId || 'SESS-7729'}</strong>
        <span className="events-view-subtitle-sep">User ID:</span>
        <strong>{meta.userId == null ? EMPTY_CELL_DISPLAY : meta.userId}</strong>
        <span className="events-view-subtitle-sep">Username:</span>
        <strong>{meta.username == null ? EMPTY_CELL_DISPLAY : meta.username}</strong>
      </p>
    </div>
  );
}
