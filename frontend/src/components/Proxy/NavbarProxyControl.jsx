import { useProxy } from '../../context/ProxyContext.jsx';
import ProxyToggleButton from './ProxyToggleButton.jsx';
import './proxy-controls.css';

export default function NavbarProxyControl() {
  const { isProxyActive, toggleProxy } = useProxy();

  return (
    <div className="navbar-proxy-control">
      <span
        className={`navbar-proxy-control__title ${isProxyActive ? 'navbar-proxy-control__title--active' : ''}`}
      >
        {isProxyActive ? 'Proxy Active' : 'Activate Proxy'}
      </span>
      <ProxyToggleButton
        isActive={isProxyActive}
        onToggle={toggleProxy}
        ariaLabel={
          isProxyActive ? 'Deactivate AgentGuard proxy' : 'Activate AgentGuard proxy'
        }
      />
    </div>
  );
}
