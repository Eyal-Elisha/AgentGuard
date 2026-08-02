import { normalizeAgentName } from '../../constants/agentOptions.js';
import AgentIcon from './AgentIcon.jsx';
import './AgentDisplay.css';

export default function AgentDisplay({ agentName, className = '' }) {
  const displayName = normalizeAgentName(agentName) || agentName || '';
  const rootClass = ['agent-display', className].filter(Boolean).join(' ');

  return (
    <span className={rootClass}>
      <AgentIcon agentName={displayName} />
      <span className="agent-display__name">{displayName}</span>
    </span>
  );
}
