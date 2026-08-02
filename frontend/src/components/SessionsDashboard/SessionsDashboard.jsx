import { useState, useEffect, useMemo, useRef } from 'react';
import SessionSearchBar from './SessionSearchBar.jsx';
import SessionsTable from './SessionsTable.jsx';
import SessionUserFilter from './SessionUserFilter.jsx';
import { useSessions } from '../../hooks/useSessions.js';
import { useDeleteSession } from '../../hooks/useDeleteSession.js';
import { useProxy } from '../../context/ProxyContext.jsx';
import { useAuth } from '../../context/AuthContext.jsx';
import { useAdminUsers } from '../../hooks/useAdminUsers.js';
import './SessionsDashboard.css';

function SessionsDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [userFilter, setUserFilter] = useState('all');
  const { currentUser } = useAuth();
  const isAdmin = Boolean(currentUser?.isAdmin);
  const { users } = useAdminUsers(isAdmin);
  const { filteredSessions, sessions, isLoading, error, refresh, removeSession } = useSessions(searchTerm);
  const { deleteSession, isPending: deletePending, error: deleteError } = useDeleteSession();
  const showTable = !isLoading && !error;

  const visibleSessions = useMemo(() => {
    if (!isAdmin || userFilter === 'all') return filteredSessions;
    if (userFilter === 'admins' || userFilter === 'users') {
      const targetIsAdmin = userFilter === 'admins';
      const matchingIds = new Set(users.filter((u) => Boolean(u.is_admin) === targetIsAdmin).map((u) => u.user_id));
      return filteredSessions.filter((s) => matchingIds.has(s.user_id));
    }
    const id = Number(userFilter);
    return filteredSessions.filter((s) => Number(s.user_id) === id);
  }, [filteredSessions, userFilter, isAdmin, users]);

  const { isProxyActive } = useProxy();
  const prevProxyActive = useRef(isProxyActive);

  useEffect(() => {
    if (prevProxyActive.current !== isProxyActive) {
      // Small delay on activation gives backend proxy time to create session
      if (!prevProxyActive.current && isProxyActive) {
        setTimeout(refresh, 500);
      } else {
        refresh();
      }
    }
    prevProxyActive.current = isProxyActive;
  }, [isProxyActive, refresh]);

  return (
    <div className="sessions-page">
      <main className="sessions-dashboard-main">
        <div className="sessions-dashboard-card sessions-dashboard-card--fit-content">
          <div className="sessions-dashboard-card-header" data-tour="sessions-main">
            <h1 className="sessions-title">Sessions</h1>
            <div className="sessions-header-controls">
              {isAdmin && (
                <SessionUserFilter
                  value={userFilter}
                  onChange={setUserFilter}
                  users={users}
                  disabled={!showTable}
                />
              )}
              <SessionSearchBar
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
                disabled={!showTable}
              />
            </div>
          </div>

          {isLoading && (
            <div className="sessions-loading" role="status" aria-live="polite">
              Loading sessions...
            </div>
          )}

          {error && (
            <div className="sessions-error-alert" role="alert">
              {error}
            </div>
          )}

          {showTable && (
            <SessionsTable
              filteredSessions={visibleSessions}
              sessions={sessions}
              onDeleteSession={deleteSession}
              deleteState={{ isPending: deletePending, error: deleteError }}
              removeSession={removeSession}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default SessionsDashboard;
