import { useAgent } from '../../context/AgentContext.jsx';
import { useProxy } from '../../context/ProxyContext.jsx';
import SessionAgentSelector from '../SessionsDashboard/SessionAgentSelector.jsx';
import PowerIcon from '../Proxy/PowerIcon.jsx';
import GuardStatus from './GuardStatus.jsx';
import './Guard.css';

const host = import.meta.env.VITE_PROXY_HOST?.trim() || '127.0.0.1';
const port = import.meta.env.VITE_PROXY_PORT?.trim() || '8080';

export default function Guard() {
  const { isProxyActive, toggleProxy, isPassiveMode, togglePassiveMode } = useProxy();
  const { selectedAgent, setSelectedAgent } = useAgent();

  return (
    <main className="guard-page">
      <div className="guard-card">
        <header className="guard-heading">
          <h1 className="guard-title">Guard</h1>
          <p className="guard-tagline">Turn on protection for your agent</p>
        </header>

        <div className="guard-agent-row" data-tour="agent">
          <SessionAgentSelector
            selectedAgent={selectedAgent}
            onAgentSelect={setSelectedAgent}
          />
        </div>

        <div className="guard-power-block">
          <button
            type="button"
            className={`guard-power-button ${isProxyActive ? 'guard-power-button--on' : 'guard-power-button--off'}`}
            onClick={toggleProxy}
            aria-pressed={isProxyActive}
            aria-label={isProxyActive ? 'Turn protection off' : 'Turn protection on'}
            data-tour="power"
          >
            <PowerIcon className="guard-power-icon" />
          </button>
        </div>

        <GuardStatus
          isProxyActive={isProxyActive}
          isPassiveMode={isPassiveMode}
          togglePassiveMode={togglePassiveMode}
        />

        <dl className="guard-endpoints">
          <div className="guard-endpoint-row">
            <dt>Proxy address</dt>
            <dd>{host}</dd>
          </div>
          <div className="guard-endpoint-row">
            <dt>Port</dt>
            <dd>{port}</dd>
          </div>
        </dl>
      </div>
    </main>
  );
}
