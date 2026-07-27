import { AGENT_OPTIONS } from '../../constants/agentOptions.js';
import AgentDisplay from '../Agents/AgentDisplay.jsx';
import StyledSelect from '../ui/StyledSelect.jsx';
import './agent-selector.css';

export default function SessionAgentSelector({
  selectedAgent,
  onAgentSelect,
}) {
  const options = AGENT_OPTIONS.map((agent) => ({
    value: agent,
    label: agent,
  }));

  return (
    <div className="agent-selector">
      <span className="agent-selector-label">SELECT AGENT</span>
      <StyledSelect
        value={selectedAgent}
        onChange={onAgentSelect}
        options={options}
        ariaLabel="Select agent"
        renderValue={() => <AgentDisplay agentName={selectedAgent} />}
        renderOption={(opt) => <AgentDisplay agentName={opt.value} />}
      />
    </div>
  );
}
