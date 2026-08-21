import AgentDisplay from '../Agents/AgentDisplay.jsx';

/** One selected agent: the endpoint to point it at, and its live status.
 *  Starting and stopping is the power button's job, which acts on the whole
 *  selection, so the row itself carries no control. */
export default function GuardAgentRow({ agentName, host, state, pendingAction }) {
  const isActive = Boolean(state?.active);
  const port = state?.proxyPort;
  const statusLabel = pendingAction === 'start'
    ? 'Starting…'
    : pendingAction === 'stop'
      ? 'Stopping…'
      : isActive ? 'Active' : 'Inactive';

  return (
    <li className={`guard-agent-row guard-agent-row--${isActive ? 'active' : 'inactive'}`}>
      <AgentDisplay agentName={agentName} className="guard-agent-name" />

      <span className="guard-agent-endpoint">
        {port == null ? 'Checking…' : `${host}:${port}`}
      </span>

      <span
        className={`guard-agent-status ${pendingAction ? `guard-agent-status--${pendingAction}` : ''}`}
        aria-live="polite"
      >
        {statusLabel}
      </span>
    </li>
  );
}
