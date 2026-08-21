import browserOsIcon from '../../assets/agents/browseros.png';
import microsoftEdgeIcon from '../../assets/agents/microsoft-edge.svg';
import './AgentIcon.css';

const AGENT_ICON_SRC = {
  BrowserOS: browserOsIcon,
  MicrosoftEdge: microsoftEdgeIcon,
};

/** All traffic is not a product, so it has no logo. A globe stands for the
 *  system-wide interception it does. */
function AllTrafficIcon() {
  return (
    <svg
      className="agent-icon agent-icon--glyph"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3Z" />
    </svg>
  );
}

/** Expects a canonical agent name (see AgentDisplay). */
export default function AgentIcon({ agentName }) {
  const name = typeof agentName === 'string' ? agentName : '';
  if (name === 'AllTraffic') return <AllTrafficIcon />;

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
