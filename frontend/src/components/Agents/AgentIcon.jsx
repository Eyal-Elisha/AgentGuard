import browserOsIcon from '../../assets/agents/browseros.png';
import microsoftEdgeIcon from '../../assets/agents/microsoft-edge.svg';
import './AgentIcon.css';

const AGENT_ICON_SRC = {
  BrowserOS: browserOsIcon,
  MicrosoftEdge: microsoftEdgeIcon,
};

/** Expects a canonical agent name (see AgentDisplay). */
export default function AgentIcon({ agentName }) {
  const name = typeof agentName === 'string' ? agentName : '';
  const src = AGENT_ICON_SRC[name];
  if (!src) return null;

  return (
    <img
      className="agent-icon"
      src={src}
      alt=""
      aria-hidden="true"
      decoding="async"
      draggable={false}
    />
  );
}
