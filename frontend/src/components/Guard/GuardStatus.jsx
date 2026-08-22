import ProxyToggleButton from '../Proxy/ProxyToggleButton.jsx';

/** The system-wide footer under the per-agent rows. Enforcement is not per
 *  agent: every instance calls the one backend, so passive mode covers them
 *  all. */
export default function GuardStatus({ activeCount, totalCount, isPassiveMode, togglePassiveMode }) {
  const isProxyActive = activeCount > 0;

  return (
    <div className={`guard-status guard-status--${isProxyActive ? 'active' : 'inactive'}`}>
      <div className="guard-status-main">
        <span className="guard-status-label">Protecting</span>
        <span className="guard-status-value">
          {activeCount} of {totalCount} {totalCount === 1 ? 'agent' : 'agents'}
        </span>
      </div>
      {isProxyActive && <div className="guard-status-divider" />}
      {isProxyActive && (
        <div className="guard-status-passive">
          <span className={`guard-status-passive-label ${!isPassiveMode ? 'guard-status-passive-label--active' : ''}`}>
            {isPassiveMode ? 'Passive' : 'Enforcing'}
          </span>
          <ProxyToggleButton
            isActive={!isPassiveMode}
            onToggle={togglePassiveMode}
            ariaLabel={isPassiveMode ? 'Switch to enforcing mode' : 'Switch to passive mode'}
            className="guard-status-passive-toggle"
          />
        </div>
      )}
    </div>
  );
}
