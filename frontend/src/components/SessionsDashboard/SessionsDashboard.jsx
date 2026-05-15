import { useState } from 'react';
import SessionSearchBar from './SessionSearchBar.jsx';
import SessionsTable from './SessionsTable.jsx';
import { useSessions } from '../../hooks/useSessions.js';
import { useDeleteSession } from '../../hooks/useDeleteSession.js';
import './SessionsDashboard.css';

function SessionsDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const { filteredSessions, sessions, isLoading, error, removeSession } = useSessions(searchTerm);
  const { deleteSession, isPending: deletePending, error: deleteError } = useDeleteSession(removeSession);
  const showTable = !isLoading && !error;

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
