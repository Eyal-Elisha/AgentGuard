import { useState } from 'react';
import { useAgent } from '../../context/AgentContext.jsx';
import SessionAgentSelector from '../SessionsDashboard/SessionAgentSelector.jsx';

export default function NavbarAgentToolbar() {
  const { selectedAgent, setSelectedAgent } = useAgent();
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);

  return (
    <SessionAgentSelector
      selectedAgent={selectedAgent}
      agentDropdownOpen={agentDropdownOpen}
      onToggleAgentDropdown={() => setAgentDropdownOpen((open) => !open)}
      onCloseAgentDropdown={() => setAgentDropdownOpen(false)}
      onAgentSelect={(agent) => {
        setSelectedAgent(agent);
        setAgentDropdownOpen(false);
      }}
    />
  );
}
