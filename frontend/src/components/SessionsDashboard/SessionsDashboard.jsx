import { useState, useEffect, useRef } from 'react';
import SessionSearchBar from './SessionSearchBar.jsx';
import SessionsTable from './SessionsTable.jsx';
import { useSessions } from '../../hooks/useSessions.js';
import { useDeleteSession } from '../../hooks/useDeleteSession.js';
import { useProxy } from '../../context/ProxyContext.jsx';
import './SessionsDashboard.css';

function SessionsDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const { filteredSessions, sessions, isLoading, error, refresh, removeSession } = useSessions(searchTerm);
  const { deleteSession, isPending: deletePending, error: deleteError } = useDeleteSession(removeSession);
  const showTable = !isLoading && !error;

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
        <div className="sessions-dashboard-card">
          <div className="sessions-dashboard-card-header">
            <h1 className="sessions-title">Sessions</h1>
            <SessionSearchBar
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              disabled={!showTable}
            />
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
              filteredSessions={filteredSessions}
              sessions={sessions}
              onDeleteSession={deleteSession}
              deleteState={{ isPending: deletePending, error: deleteError }}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default SessionsDashboard;
