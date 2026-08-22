import { agentLabel, normalizeAgentName } from '../../constants/agentOptions.js';
import AgentIcon from './AgentIcon.jsx';
import './AgentDisplay.css';

export default function AgentDisplay({ agentName, className = '' }) {
  const canonical = normalizeAgentName(agentName) || agentName || '';
  const displayName = agentLabel(agentName) || canonical;
  const rootClass = ['agent-display', className].filter(Boolean).join(' ');

  return (
    <span className={rootClass}>
      <AgentIcon agentName={canonical} />
      <span className="agent-display__name">{displayName}</span>
    </span>
  );
}
