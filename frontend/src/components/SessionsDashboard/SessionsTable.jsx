import {
  EMPTY_CELL_DISPLAY,
  formatIsoLocal,
  isIsoEmpty,
} from './sessionUtils.js';

// TODO: Risk score thresholds (low, medium, high) are currently hardcoded for the mockup and should be configurable or driven by the backend in the future.
function getRiskLevel(score) {
  if (score > 0.7) return 'high';
  if (score > 0.4) return 'medium';
  return 'low';
}

export default function SessionsTable({
  filteredSessions,
  sessions,
}) {
  return (
    <div className="sessions-table-wrapper">
      <table className="sessions-table">
        <thead>
          <tr>
            <th>AGENT NAME</th>
            <th>SESSION ID</th>
            <th>USER ID</th>
            <th className="th-risk-center">AVERAGE RISK SCORE</th>
            <th className="th-centered-block">START TIME</th>
            <th className="th-centered-block">END TIME</th>
          </tr>
        </thead>
        <tbody>
          {filteredSessions.map((session) => {
            const riskLevel = getRiskLevel(session.average_risk_score);
            const userIdEmpty = session.user_id == null;
            const startEmpty = isIsoEmpty(session.start_time);
            const endEmpty = isIsoEmpty(session.end_time);
            return (
              <tr key={session.session_id} className="sessions-row">
                <td className="cell-agent-name">{session.agent_name}</td>
                <td className="cell-session-id">{session.session_id}</td>
                <td
                  className={`cell-user-id${
                    userIdEmpty ? ' cell-value-empty' : ''
                  }`}
                >
                  {userIdEmpty ? EMPTY_CELL_DISPLAY : session.user_id}
                </td>
                <td className={`cell-risk cell-risk--${riskLevel} td-risk-center`}>
                  <span className="cell-risk-inner">
                    {session.average_risk_score.toFixed(2)}
                  </span>
                </td>
                {/* TODO: Check if backend can provide pre-formatted timestamps */}
                <td
                  className={`cell-timestamp td-centered-block${
                    startEmpty ? ' cell-value-empty' : ''
                  }`}
                >
                  {formatIsoLocal(session.start_time)}
                </td>
                <td
                  className={`cell-timestamp td-centered-block${
                    endEmpty ? ' cell-value-empty' : ''
                  }`}
                >
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
  );
}
