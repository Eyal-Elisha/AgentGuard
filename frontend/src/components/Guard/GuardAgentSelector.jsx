import { AGENT_OPTIONS, ALL_TRAFFIC_AGENT, agentLabel } from '../../constants/agentOptions.js';
import AgentDisplay from '../Agents/AgentDisplay.jsx';
import StyledSelect from '../ui/StyledSelect.jsx';
import './GuardAgentSelector.css';

/* All traffic sits above the rule, the named agents below it: picking across
   the rule replaces rather than adds, so the divider is where the two modes
   part company. */
const options = [
  { value: ALL_TRAFFIC_AGENT, label: agentLabel(ALL_TRAFFIC_AGENT) },
  { divider: true },
  ...AGENT_OPTIONS.filter((agent) => agent !== ALL_TRAFFIC_AGENT).map((agent) => ({
    value: agent,
    label: agentLabel(agent),
  })),
];

/** Which agents the power button acts on. Several named agents may be picked
 *  at once, since each runs behind its own proxy instance. */
export default function GuardAgentSelector({ selectedAgents, onSelect, disabled }) {
  function summary(values) {
    if (!values || values.length === 0) return 'No agents selected';
    if (values.length === 1) return <AgentDisplay agentName={values[0]} />;
    return `${values.length} agents`;
  }

  return (
    <div className="guard-agent-selector">
      <span className="guard-agent-selector-label">SELECT AGENTS</span>
      <StyledSelect
        multiple
        value={selectedAgents}
        onChange={onSelect}
        options={options}
        disabled={disabled}
        ariaLabel="Select what to protect"
        renderValue={summary}
        renderOption={(opt) => <AgentDisplay agentName={opt.value} />}
      />
    </div>
  );
}
