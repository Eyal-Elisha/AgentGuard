import './EventBlockReason.css';

function triggeredDetails(rows) {
  return rows
    .filter((row) => typeof row.rule_score === 'number' && row.rule_score > 0)
    .map((row) => row.details)
    .filter(Boolean);
}

export default function EventBlockReason({ selectedEvent, ruleAnalysisRows }) {
  if (selectedEvent?.guard_action !== 'Block') return null;

  const details = triggeredDetails(ruleAnalysisRows);
  const reason = details[0] ?? 'AgentGuard blocked this request based on its risk analysis.';

  return (
    <div className="event-block-reason" role="note">
      <strong>Blocked reason:</strong>
      <span>{reason}</span>
    </div>
  );
}
