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
        <h1 className="home-title">Proxy Control</h1>
        <p className="home-tagline">AgentGuard Home</p>
        <div className="home-agent-row">
          <SessionAgentSelector
            selectedAgent={selectedAgent} agentDropdownOpen={agentDropdownOpen}
            onToggleAgentDropdown={() => setAgentDropdownOpen((o) => !o)}
            onCloseAgentDropdown={() => setAgentDropdownOpen(false)}
            onAgentSelect={(a) => { setSelectedAgent(a); setAgentDropdownOpen(false); }}
          />
        </div>
        <div className="home-power-block">
          <button
            type="button" className={`home-power-button ${isProxyActive ? 'home-power-button--on' : 'home-power-button--off'}`}
            onClick={toggleProxy} aria-pressed={isProxyActive}
          >
            <PowerIcon className="home-power-icon" />
          </button>
        </div>
        <HomeStatus isProxyActive={isProxyActive} isPassiveMode={isPassiveMode} togglePassiveMode={togglePassiveMode} />
        <dl className="home-endpoints">
          <div className="home-endpoint-row"><dt>Proxy address</dt><dd>{host}</dd></div>
          <div className="home-endpoint-row"><dt>Port</dt><dd>{port}</dd></div>
        </dl>
        <section className="home-copy">
          <h2 className="home-copy-heading">What this does</h2>
          <p>Activating AgentGuard sends a start request to the backend... traffic recorded in sessions and events.</p>
          <h2 className="home-copy-heading">System and app settings</h2>
          <p className="home-copy-note">Traffic is only routed through AgentGuard if configured... turning off closes the session.</p>
        </section>
      </div>
    </main>
  );
}
