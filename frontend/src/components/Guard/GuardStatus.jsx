import ProxyToggleButton from '../Proxy/ProxyToggleButton.jsx';

export default function GuardStatus({ isProxyActive, isPassiveMode, togglePassiveMode }) {
  return (
    <div className={`guard-status guard-status--${isProxyActive ? 'active' : 'inactive'}`}>
      <div className="guard-status-main">
        <span className="guard-status-label">Proxy status</span>
        <span className="guard-status-value">{isProxyActive ? 'Active' : 'Inactive'}</span>
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
