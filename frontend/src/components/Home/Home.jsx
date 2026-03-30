import { useState } from 'react';
import { useAgent } from '../../context/AgentContext.jsx';
import { useProxy } from '../../context/ProxyContext.jsx';
import SessionAgentSelector from '../SessionsDashboard/SessionAgentSelector.jsx';
import PowerIcon from '../Proxy/PowerIcon.jsx';
import './Home.css';

function getProxyHost() {
  const raw = import.meta.env.VITE_PROXY_HOST;
  return raw != null && String(raw).trim() !== '' ? String(raw).trim() : '127.0.0.1';
}

function getProxyPort() {
  const raw = import.meta.env.VITE_PROXY_PORT;
  if (raw != null && String(raw).trim() !== '') {
    const n = Number.parseInt(String(raw).trim(), 10);
    if (!Number.isNaN(n)) return String(n);
  }
  return '8080';
}

export default function Home() {
  const { isProxyActive, toggleProxy } = useProxy();
  const { selectedAgent, setSelectedAgent } = useAgent();
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);
  const host = getProxyHost();
  const port = getProxyPort();

  return (
    <main className="home-page">
      <div className="home-card">
        <h1 className="home-title">Proxy Control</h1>
        <p className="home-tagline">AgentGuard Home</p>

        <div className="home-agent-row">
          <SessionAgentSelector
            selectedAgent={selectedAgent}
            agentDropdownOpen={agentDropdownOpen}
            onToggleAgentDropdown={() =>
              setAgentDropdownOpen((open) => !open)
            }
            onCloseAgentDropdown={() => setAgentDropdownOpen(false)}
            onAgentSelect={(agent) => {
              setSelectedAgent(agent);
              setAgentDropdownOpen(false);
            }}
          />
        </div>

        <div className="home-power-block">
          <button
            type="button"
            className={`home-power-button ${isProxyActive ? 'home-power-button--on' : 'home-power-button--off'}`}
            onClick={toggleProxy}
            aria-pressed={isProxyActive}
            aria-label={
              isProxyActive ? 'Deactivate AgentGuard proxy' : 'Activate AgentGuard proxy'
            }
          >
            <PowerIcon className="home-power-icon" />
          </button>
        </div>

        <div className={`home-status home-status--${isProxyActive ? 'active' : 'inactive'}`}>
          <span className="home-status-label">Proxy status</span>
          <span className="home-status-value">
            {isProxyActive ? 'Active' : 'Inactive'}
          </span>
        </div>

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

        <section className="home-copy">
          <h2 className="home-copy-heading">What this does</h2>
          <p>
            Activating AgentGuard sends a start request to the backend, which launches the
            mitmproxy pipeline and opens a new AgentGuard session for the selected environment. When
            active, traffic that actually goes through this proxy can be inspected, evaluated, and
            recorded in sessions and events.
          </p>
          <h2 className="home-copy-heading">System and app settings</h2>
          <p className="home-copy-note">
            Traffic is only routed through AgentGuard if Windows, your browser, or a protected app
            is configured to use this proxy address and port. This toggle starts or stops the
            AgentGuard proxy service and closes the active AgentGuard session when turned off, but
            it does not change OS or browser proxy settings for you.
          </p>
        </section>
      </div>
    </main>
  );
}
