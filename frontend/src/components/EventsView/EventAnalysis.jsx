import EventMetadata from './EventMetadata.jsx';
import './EventAnalysis.css';

function RuleScoreBar({ score }) {
  const pct = typeof score === 'number' ? Math.min(Math.max(score * 100, 0), 100) : 0;
  const hue = Math.round(120 - pct * 1.2); // green→red
  return (
    <div className="rule-score-bar-wrap" title={`${pct.toFixed(0)}%`}>
      <div className="rule-score-bar-track">
        <div className="rule-score-bar-fill" style={{ width: `${pct}%`, background: `hsl(${hue}, 70%, 52%)` }} />
      </div>
      <span className="rule-score-bar-label">{typeof score === 'number' ? score.toFixed(2) : '–'}</span>
    </div>
  );
}

export default function EventAnalysis({ selectedEvent, ruleAnalysisRows }) {
  const guardAction = selectedEvent?.guard_action?.toLowerCase() || '';
  const riskColorClass = guardAction ? ` events-risk-value--${guardAction}` : '';
  const eventHardBlock = ruleAnalysisRows.some(
    (row) => Boolean(row.is_hard_block) && typeof row.rule_score === 'number' && row.rule_score > 0,
  ) || ruleAnalysisRows.some((row) => Boolean(row.hard_block));

  return (
    <section className="events-analysis-pane">
      <div className="events-pane-title-row">
        <h2 className="events-pane-title">Analysis Evidence</h2>
        <span className="events-pane-pill">Event ID: {selectedEvent ? selectedEvent.event_id : '–'}</span>
      </div>

      <div className="events-risk-row">
        <div className="events-risk-card">
          <p className="events-risk-label">Event Risk Score</p>
          <p className={`events-risk-value${riskColorClass}`}>
            {selectedEvent ? selectedEvent.risk_score.toFixed(2) : '0.00'}
          </p>
        </div>
        {selectedEvent && (
          <div className={`events-hardblock-card events-hardblock-card--${eventHardBlock ? 'on' : 'off'}`}>
            <p className="events-risk-label">Hard Block</p>
            <p className="events-hardblock-value">{eventHardBlock ? 'TRIGGERED' : 'NONE'}</p>
          </div>
        )}
      </div>

      {selectedEvent && (
        <EventMetadata
          url={selectedEvent.url}
          http_method={selectedEvent.http_method}
          headers={selectedEvent.headers}
        />
      )}

      <h3 className="events-rules-title">Rules Analysis Details</h3>
      <div className="events-rules-table-wrap">
        <table className="sessions-table events-rules-table">
          <thead>
            <tr>
              <th>RULE CODE</th>
              <th>RULE TYPE</th>
              <th>WEIGHT</th>
              <th>HARD BLOCK</th>
              <th>RULE SCORE</th>
              <th>DETAILS</th>
            </tr>
          </thead>
          <tbody>
            {ruleAnalysisRows.map((row) => {
              const hard = Boolean(row.is_hard_block ?? row.hard_block);
              return (
                <tr key={row.analysis_id} className="sessions-row">
                  <td>{row.rule_code}</td>
                  <td>{row.rule_type || '–'}</td>
                  <td>{row.weight != null ? row.weight : '–'}</td>
                  <td>
                    <span className={`rules-badge ${hard ? 'rules-badge--hard-block' : 'rules-badge--neutral'}`}>
                      {hard ? 'Yes' : 'No'}
                    </span>
                  </td>
                  <td><RuleScoreBar score={row.rule_score} /></td>
                  <td>{row.details}</td>
                </tr>
              );
            })}
            {ruleAnalysisRows.length === 0 && (
              <tr><td colSpan={6} className="sessions-empty-state">No analysis for this event yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
