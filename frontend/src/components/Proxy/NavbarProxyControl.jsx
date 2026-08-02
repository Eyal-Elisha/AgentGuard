import { useProxy } from '../../context/ProxyContext.jsx';
import ProxyToggleButton from './ProxyToggleButton.jsx';
import './proxy-controls.css';

export default function NavbarProxyControl() {
  const { isProxyActive, toggleProxy, isProxyPending } = useProxy();

  const title = isProxyPending
    ? (isProxyActive ? 'Stopping…' : 'Starting…')
    : (isProxyActive ? 'Proxy Active' : 'Activate Proxy');

  return (
    <div className="navbar-proxy-control">
      <span
        className={`navbar-proxy-control__title ${isProxyActive ? 'navbar-proxy-control__title--active' : ''} ${isProxyPending ? 'navbar-proxy-control__title--pending' : ''}`}
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
