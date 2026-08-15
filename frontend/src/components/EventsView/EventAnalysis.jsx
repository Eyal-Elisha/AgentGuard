import EventMetadata from './EventMetadata.jsx';
import RulesAnalysisSection from './RulesAnalysisSection.jsx';
import { groupRuleAnalysisSections } from './eventAnalysisUtils.js';
import './eventAnalysis/index.css';

export default function EventAnalysis({ selectedEvent, ruleAnalysisRows }) {
  const guardAction = selectedEvent?.guard_action?.toLowerCase() || '';
  const riskColorClass = guardAction ? ` events-risk-value--${guardAction}` : '';
  // `hard_block` on an analysis row records whether that rule hard-blocked this
  // request. `is_hard_block` on the rule only says it is allowed to, which is
  // true of a couple of rules on every event, so it must not be consulted here.
  const eventHardBlock = ruleAnalysisRows.some((row) => Boolean(row.hard_block));

  const sections = groupRuleAnalysisSections(ruleAnalysisRows);

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
          <EventMetadata
            url={selectedEvent.url}
            http_method={selectedEvent.http_method}
            headers={selectedEvent.headers}
          />
        )}
        {selectedEvent && (
          <div className={`events-hardblock-card events-hardblock-card--${eventHardBlock ? 'on' : 'off'}`}>
            <p className="events-risk-label">Hard Block</p>
            <p className="events-hardblock-value">{eventHardBlock ? 'TRIGGERED' : 'NONE'}</p>
          </div>
        )}
      </div>

      {sections.length === 0 ? (
        <div className="events-rules-details events-rules-details--empty">
          <p className="sessions-empty-state">No analysis for this event yet.</p>
        </div>
      ) : (
        <div className="events-rules-details">
          <h3 className="events-rules-details-heading">Rules analysis details</h3>
          {sections.map((section) => (
            <RulesAnalysisSection
              key={`${selectedEvent?.event_id ?? 'none'}-${section.type}`}
              section={section}
            />
          ))}
        </div>
      )}
    </section>
  );
}
