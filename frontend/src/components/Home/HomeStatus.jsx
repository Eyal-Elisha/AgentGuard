import ProxyToggleButton from '../Proxy/ProxyToggleButton.jsx';

export default function HomeStatus({ isProxyActive, isPassiveMode, togglePassiveMode }) {
  return (
    <div className={`home-status home-status--${isProxyActive ? 'active' : 'inactive'}`}>
      <div className="home-status-main">
        <span className="home-status-label">Proxy status</span>
        <span className="home-status-value">{isProxyActive ? 'Active' : 'Inactive'}</span>
      </div>
      {isProxyActive && <div className="home-status-divider" />}
      {isProxyActive && (
        <div className="home-status-passive">
          <span className={`home-status-passive-label ${!isPassiveMode ? 'home-status-passive-label--active' : ''}`}>
            {isPassiveMode ? 'Passive' : 'Enforcing'}
          </span>
          <ProxyToggleButton
            isActive={!isPassiveMode}
            onToggle={togglePassiveMode}
            ariaLabel={isPassiveMode ? 'Switch to enforcing mode' : 'Switch to passive mode'}
            className="home-status-passive-toggle"
          />
        </div>
      )}
    </div>
  );
}
