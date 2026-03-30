export default function EventAnalysis({
  selectedEvent,
  ruleAnalysisRows,
}) {
  const guardAction = selectedEvent?.guard_action?.toLowerCase() || '';
  const riskColorClass = guardAction ? ` events-risk-value--${guardAction}` : '';

  return (
    <section className="events-analysis-pane">
      <div className="events-pane-title-row">
        <h2 className="events-pane-title">Analysis Evidence</h2>
        <span className="events-pane-pill">
          Event ID: {selectedEvent ? selectedEvent.event_id : '–'}
        </span>
      </div>

      <div className="events-risk-card">
        <p className="events-risk-label">Event Risk Score</p>
        <p className={`events-risk-value${riskColorClass}`}>
          {selectedEvent ? selectedEvent.risk_score.toFixed(2) : '0.00'}
        </p>
      </div>

      <h3 className="events-rules-title">Rules Analysis Details</h3>
      <div className="events-rules-table-wrap">
        <table className="sessions-table events-rules-table">
          <thead>
            <tr>
              <th>RULE CODE</th>
              <th>RULE TYPE</th>
              <th>WEIGHT</th>
              <th>RULE SCORE</th>
              <th>DETAILS</th>
            </tr>
          </thead>
          <tbody>
            {ruleAnalysisRows.map((row) => (
              <tr key={row.analysis_id} className="sessions-row">
                <td>{row.rule_code}</td>
                <td>{row.rule_type || '-'}</td>
                <td>{row.weight !== undefined && row.weight !== null ? row.weight : '-'}</td>
                <td>{row.rule_score !== undefined && row.rule_score !== null ? row.rule_score.toFixed(2) : '-'}</td>
                <td>{row.details}</td>
              </tr>
            ))}
            {ruleAnalysisRows.length === 0 && (
              <tr>
                <td colSpan={5} className="sessions-empty-state">
                  No analysis for this event yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
