import { AGENT_OPTIONS } from '../../constants/agentOptions.js';
import './agent-selector.css';

export default function SessionAgentSelector({
  selectedAgent,
  agentDropdownOpen,
  onToggleAgentDropdown,
  onCloseAgentDropdown,
  onAgentSelect,
}) {
  return (
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
  );
}
