import { NavLink } from 'react-router-dom';
import ShieldIcon from './ShieldIcon.jsx';

const AGENT_OPTIONS = ['Gemini', 'BrowserOS'];

function navTabClass({ isActive }) {
  return `nav-tab${isActive ? ' nav-tab--active' : ''}`;
}

export default function SessionsDashboardHeader({
  selectedAgent,
  agentDropdownOpen,
  onToggleAgentDropdown,
  onCloseAgentDropdown,
  onAgentSelect,
  isProxyActive,
  onProxyToggle,
  showAgentControls = true,
}) {
  return (
    <header className="sessions-dashboard-header">
      <div className="sessions-dashboard-brand">
        <ShieldIcon />
        <span>AgentGuard</span>
      </div>
      <nav className="sessions-dashboard-nav" aria-label="Primary">
        <NavLink to="/" end className={navTabClass}>
          Sessions
        </NavLink>
        <NavLink to="/rules" className={navTabClass}>
          Rules
        </NavLink>
      </nav>
      {showAgentControls ? (
      <div className="sessions-dashboard-header-right">
        <div className="agent-selector">
          <span className="agent-selector-label">SELECT AGENT</span>
          <div className="agent-select-wrap">
            <button
              type="button"
              className="agent-select"
              onClick={onToggleAgentDropdown}
              onBlur={onCloseAgentDropdown}
              aria-haspopup="listbox"
              aria-expanded={agentDropdownOpen}
              aria-label="Select agent"
            >
              {selectedAgent}
            </button>
            {agentDropdownOpen && (
              <div className="agent-select-options" role="listbox">
                {AGENT_OPTIONS.map((agent) => (
                  <button
                    key={agent}
                    type="button"
                    role="option"
                    aria-selected={selectedAgent === agent}
                    className={`agent-select-option ${selectedAgent === agent ? 'agent-select-option--active' : ''}`}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      onAgentSelect(agent);
                    }}
                  >
                    {agent}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="sessions-dashboard-proxy">
          <span className="proxy-label">PROXY</span>
          <button
            type="button"
            className={`proxy-toggle ${isProxyActive ? 'proxy-toggle--on' : 'proxy-toggle--off'}`}
            onClick={onProxyToggle}
            aria-pressed={isProxyActive}
            aria-label={`Toggle proxy for ${selectedAgent}`}
          >
            <span className="proxy-knob" />
          </button>
        </div>
      </div>
      ) : (
        <div className="sessions-dashboard-header-right sessions-dashboard-header-right--spacer" aria-hidden="true" />
      )}
    </header>
  );
}
