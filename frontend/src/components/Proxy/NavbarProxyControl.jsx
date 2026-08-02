import { useProxy } from '../../context/ProxyContext.jsx';
import ProxyToggleButton from './ProxyToggleButton.jsx';
import './proxy-controls.css';

export default function NavbarProxyControl() {
  const { isProxyActive, toggleProxy, isProxyPending, proxyPendingAction } = useProxy();

  const title = proxyPendingAction === 'start'
    ? 'Starting…'
    : proxyPendingAction === 'stop'
      ? 'Stopping…'
      : (isProxyActive ? 'Proxy Active' : 'Activate Proxy');

  return (
    <div className="navbar-proxy-control">
      <span
        className={`navbar-proxy-control__title ${isProxyActive ? 'navbar-proxy-control__title--active' : ''} ${proxyPendingAction ? `navbar-proxy-control__title--${proxyPendingAction}` : ''}`}
      >
        {title}
      </span>
      <ProxyToggleButton
        isActive={isProxyActive}
        onToggle={toggleProxy}
        isPending={isProxyPending}
        ariaLabel={
          isProxyActive ? 'Deactivate AgentGuard proxy' : 'Activate AgentGuard proxy'
        }
      />
    </div>
  );
}
