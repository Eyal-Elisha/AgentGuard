import { useEffect } from 'react';
import { useProxy } from '../../context/ProxyContext.jsx';
import PowerIcon from '../Proxy/PowerIcon.jsx';
import GuardAgentRow from './GuardAgentRow.jsx';
import GuardAgentSelector from './GuardAgentSelector.jsx';
import GuardStatus from './GuardStatus.jsx';
import './Guard.css';

const host = import.meta.env.VITE_PROXY_HOST?.trim() || '127.0.0.1';

export default function Guard() {
  const {
    agents,
    selectedAgents,
    setSelectedAgents,
    isSelectionActive,
    isAllTrafficSelected,
    activeSelectedCount,
    toggleProxy,
    pendingActions,
    pendingSelectionAction,
    isPassiveMode,
    togglePassiveMode,
    refreshStatus,
  } = useProxy();

  // The provider's own call fires before sign-in and is refused, so the
  // endpoints arrive here, on the first screen that is behind the login.
  useEffect(() => { void refreshStatus(); }, [refreshStatus]);

  const isPending = Boolean(pendingSelectionAction);

  return (
    <main className="guard-page">
      <div className="guard-card">
        <header className="guard-heading">
          <h1 className="guard-title">Guard</h1>
          <p className="guard-tagline">Turn on protection for your agents</p>
        </header>

        <GuardAgentSelector
          selectedAgents={selectedAgents}
          onSelect={setSelectedAgents}
          disabled={isPending}
        />

        <div className="guard-power-block">
          <div className="guard-power-button-wrap">
            <p
              className={`guard-power-pending ${pendingSelectionAction ? `guard-power-pending--${pendingSelectionAction}` : ''}`}
              aria-live="polite"
            >
              {pendingSelectionAction === 'stop' ? 'Stopping…' : pendingSelectionAction === 'start' ? 'Starting…' : ''}
            </p>
            <button
              type="button"
              className={`guard-power-button ${isSelectionActive ? 'guard-power-button--on' : 'guard-power-button--off'} ${pendingSelectionAction ? `guard-power-button--${pendingSelectionAction}` : ''}`}
              onClick={toggleProxy}
              aria-pressed={isSelectionActive}
              aria-label={isSelectionActive ? 'Turn protection off' : 'Turn protection on'}
              disabled={isPending || selectedAgents.length === 0}
              aria-busy={isPending}
              data-tour="power"
            >
              <PowerIcon className="guard-power-icon" />
            </button>
          </div>
        </div>

        {/* One row per selected agent: each is its own proxy instance, so each
            has its own endpoint to point that agent at. */}
        <ul className="guard-agents" data-tour="agent">
          {selectedAgents.map((agentName) => (
            <GuardAgentRow
              key={agentName}
              agentName={agentName}
              host={host}
              state={agents[agentName]}
              pendingAction={pendingActions[agentName] ?? null}
            />
          ))}
        </ul>

        {/* The endpoint alone does not say what to do with it, and the two
            modes are set in different places. Named without an operating
            system, since the same two steps apply on each. */}
        <p className="guard-setup-hint">
          {isAllTrafficSelected
            ? 'Set this as your system proxy to cover everything on this machine.'
            : 'Leave the system proxy alone. Start each agent pointed at its own address.'}
        </p>

        {/* Passive mode is system-wide: every instance calls the one backend. */}
        <GuardStatus
          activeCount={activeSelectedCount}
          totalCount={selectedAgents.length}
          isPassiveMode={isPassiveMode}
          togglePassiveMode={togglePassiveMode}
        />
      </div>
    </main>
  );
}
