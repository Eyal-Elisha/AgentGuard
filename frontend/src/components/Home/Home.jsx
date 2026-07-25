import { useState } from 'react';
import { useAgent } from '../../context/AgentContext.jsx';
import { useProxy } from '../../context/ProxyContext.jsx';
import SessionAgentSelector from '../SessionsDashboard/SessionAgentSelector.jsx';
import PowerIcon from '../Proxy/PowerIcon.jsx';
import HomeStatus from './HomeStatus.jsx';
import './Home.css';

const host = import.meta.env.VITE_PROXY_HOST?.trim() || '127.0.0.1';
const port = import.meta.env.VITE_PROXY_PORT?.trim() || '8080';

export default function Home() {
  const { isProxyActive, toggleProxy, isPassiveMode, togglePassiveMode } = useProxy();
  const { selectedAgent, setSelectedAgent } = useAgent();
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);

  return (
    <main className="home-page">
      <div className="home-card">
        <header className="home-heading">
          <h1 className="home-title">Guard</h1>
          <p className="home-tagline">Turn on protection for your agent</p>
        </header>

        <div className="home-agent-row" data-tour="agent">
          <SessionAgentSelector
            selectedAgent={selectedAgent}
            agentDropdownOpen={agentDropdownOpen}
            onToggleAgentDropdown={() => setAgentDropdownOpen((o) => !o)}
            onCloseAgentDropdown={() => setAgentDropdownOpen(false)}
            onAgentSelect={(a) => { setSelectedAgent(a); setAgentDropdownOpen(false); }}
          />
        </div>

        <div className="home-power-block">
          <button
            type="button"
            className={`home-power-button ${isProxyActive ? 'home-power-button--on' : 'home-power-button--off'}`}
            onClick={toggleProxy}
            aria-pressed={isProxyActive}
            aria-label={isProxyActive ? 'Turn protection off' : 'Turn protection on'}
            data-tour="power"
          >
            <PowerIcon className="home-power-icon" />
          </button>
        </div>

        <HomeStatus
          isProxyActive={isProxyActive}
          isPassiveMode={isPassiveMode}
          togglePassiveMode={togglePassiveMode}
        />

        <dl className="home-endpoints">
          <div className="home-endpoint-row">
            <dt>Proxy address</dt>
            <dd>{host}</dd>
          </div>
          <div className="home-endpoint-row">
            <dt>Port</dt>
            <dd>{port}</dd>
          </div>
        </dl>
      </div>
    </main>
  );
}
