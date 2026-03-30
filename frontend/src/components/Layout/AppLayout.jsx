import { NavLink, Outlet } from 'react-router-dom';
import ShieldIcon from '../SessionsDashboard/ShieldIcon.jsx';
import NavbarAgentToolbar from './NavbarAgentToolbar.jsx';
import NavbarProxyControl from '../Proxy/NavbarProxyControl.jsx';
import './AppLayout.css';

export default function AppLayout() {
  return (
    <div className="app-layout agentguard-theme">
      <header className="app-header">
        <NavLink to="/" className="app-brand" end>
          <ShieldIcon />
          <span>AgentGuard</span>
        </NavLink>
        <nav className="app-nav" aria-label="Main">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `nav-tab${isActive ? ' nav-tab--active' : ''}`
            }
            end
          >
            Home
          </NavLink>
          <NavLink
            to="/sessions"
            className={({ isActive }) =>
              `nav-tab${isActive ? ' nav-tab--active' : ''}`
            }
          >
            Sessions
          </NavLink>
          <NavLink
            to="/rules"
            className={({ isActive }) =>
              `nav-tab${isActive ? ' nav-tab--active' : ''}`
            }
          >
            Rules
          </NavLink>
        </nav>
        <div className="app-header-right">
          <NavbarAgentToolbar />
          <NavbarProxyControl />
        </div>
      </header>
      <div className="app-main">
        <Outlet />
      </div>
    </div>
  );
}
