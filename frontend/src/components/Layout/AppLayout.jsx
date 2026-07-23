import { NavLink, Outlet } from 'react-router-dom';
import ShieldIcon from '../SessionsDashboard/ShieldIcon.jsx';
import NavbarAgentToolbar from './NavbarAgentToolbar.jsx';
import NavbarProxyControl from '../Proxy/NavbarProxyControl.jsx';
import { useAuth } from '../../context/AuthContext.jsx';
import './AppLayout.css';

export default function AppLayout() {
  const { currentUser, logout } = useAuth();

  return (
    <div className="app-layout agentguard-theme">
      <header className="app-header">
        <div className="app-header-left">
          <NavLink to="/" className="app-brand" end>
            <ShieldIcon />
            <span>AgentGuard</span>
          </NavLink>
          {currentUser && (
            <div className="app-user-info">
              <span className="app-user-greeting">
                Hi, <strong>{currentUser.username}</strong>
              </span>
              <button type="button" onClick={logout} className="nav-logout-btn">
                Logout
              </button>
            </div>
          )}
        </div>
        
        <div className="nav-separator" aria-hidden="true" />
        
        <nav className="app-nav" aria-label="Main">
          <NavLink to="/" className={({ isActive }) => `nav-tab${isActive ? ' nav-tab--active' : ''}`} end>
            Home
          </NavLink>
          <NavLink to="/sessions" className={({ isActive }) => `nav-tab${isActive ? ' nav-tab--active' : ''}`}>
            Sessions
          </NavLink>
          <NavLink to="/rules" className={({ isActive }) => `nav-tab${isActive ? ' nav-tab--active' : ''}`}>
            Rules
          </NavLink>
          {currentUser?.isAdmin && (
            <NavLink to="/admin" className={({ isActive }) => `nav-tab${isActive ? ' nav-tab--active' : ''}`}>
              Admin
            </NavLink>
          )}
        </nav>
        
        <div className="nav-separator" aria-hidden="true" />

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
