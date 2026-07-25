import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import ShieldIcon from '../SessionsDashboard/ShieldIcon.jsx';
import HelpIcon from '../Help/HelpIcon.jsx';
import HelpDrawer from '../Help/HelpDrawer.jsx';
import { TourProvider } from '../../onboarding/TourProvider.jsx';
import TourOverlay from '../../onboarding/TourOverlay.jsx';
import { useAuth } from '../../context/AuthContext.jsx';
import './AppLayout.css';

const HELP_PANEL_ID = 'app-help-panel';

export default function AppLayout() {
  const { currentUser, logout } = useAuth();
  const [helpOpen, setHelpOpen] = useState(false);

  return (
    <TourProvider>
      <div className="app-layout agentguard-theme">
        <header className="app-header">
          <div className="app-header-left">
            <NavLink to="/" className="app-brand" end>
              <ShieldIcon />
              <span>AgentGuard</span>
            </NavLink>
            <button
              type="button"
              className="app-help-btn"
              aria-label="Help"
              title="Help"
              aria-expanded={helpOpen}
              aria-controls={HELP_PANEL_ID}
              aria-haspopup="dialog"
              onClick={() => setHelpOpen(true)}
            >
              <HelpIcon />
              <span className="app-help-btn-label">Help</span>
            </button>
          </div>

          <nav className="app-nav" aria-label="Main">
            <NavLink
              to="/"
              className={({ isActive }) => `nav-tab${isActive ? ' nav-tab--active' : ''}`}
              end
              data-tour="nav-guard"
            >
              Guard
            </NavLink>
            <NavLink
              to="/sessions"
              className={({ isActive }) => `nav-tab${isActive ? ' nav-tab--active' : ''}`}
              data-tour="nav-sessions"
            >
              Sessions
            </NavLink>
            <NavLink
              to="/rules"
              className={({ isActive }) => `nav-tab${isActive ? ' nav-tab--active' : ''}`}
              data-tour="nav-rules"
            >
              Rules
            </NavLink>
            {currentUser?.isAdmin && (
              <NavLink to="/admin" className={({ isActive }) => `nav-tab${isActive ? ' nav-tab--active' : ''}`}>
                Admin
              </NavLink>
            )}
          </nav>

          <div className="app-header-right">
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
        </header>

        <div className="app-main">
          <Outlet />
        </div>

        <HelpDrawer id={HELP_PANEL_ID} open={helpOpen} onClose={() => setHelpOpen(false)} />
        <TourOverlay />
      </div>
    </TourProvider>
  );
}
