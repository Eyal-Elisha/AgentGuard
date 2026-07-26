import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { EMPTY_CELL_DISPLAY, formatIsoLocal, isIsoEmpty } from './sessionUtils.js';
import AgentDisplay from '../Agents/AgentDisplay.jsx';
import DeleteSessionModal from './DeleteSessionModal.jsx';
import SessionStatusBadge from './SessionStatusBadge.jsx';

function getRiskLevel(score) {
  if (score > 0.7) return 'high';
  if (score > 0.4) return 'medium';
  return 'low';
}

function TrashIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  );
}

export default function SessionsTable({ filteredSessions, sessions, onDeleteSession, deleteState, removeSession }) {
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  const canDeleteSessions = Boolean(currentUser?.isAdmin);
  const [sessionToDelete, setSessionToDelete] = useState(null);
  const [animatingDeleteId, setAnimatingDeleteId] = useState(null);

  function handleDeleteClick(e, session) {
    e.stopPropagation();
    setSessionToDelete(session);
  }

  async function handleConfirmDelete() {
    if (!sessionToDelete) return;
    const sessionId = sessionToDelete.session_id;

    const ok = await onDeleteSession(sessionId);
    if (ok) {
      setSessionToDelete(null); // hide modal only on success
      setAnimatingDeleteId(sessionId);
      setTimeout(() => {
        if (removeSession) removeSession(sessionId);
      }, 300);
    }
  }

  return (
    <>
      <div className="sessions-table-wrapper">
        <table className="sessions-table">
          <thead>
            <tr>
              <th>AGENT NAME</th>
              <th>SESSION ID</th>
              <th className="th-centered">STATUS</th>
              <th className="th-centered">USER ID</th>
              <th className="th-centered">AVG RISK</th>
              <th className="th-centered-block">START TIME</th>
              <th className="th-centered-block">END TIME</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {filteredSessions.map((session) => {
              const riskLevel = getRiskLevel(session.average_risk_score);
              const isClosed = !isIsoEmpty(session.end_time);
              const isDeleting = animatingDeleteId === session.session_id;
              return (
                <tr key={session.session_id} className={`sessions-row ${isDeleting ? 'sessions-row-deleting' : ''}`} onClick={() => navigate(`/sessions/${session.session_id}/events`)}>
                  <td className="cell-agent-name">
                    <AgentDisplay agentName={session.agent_name} />
                  </td>
                  <td className="cell-session-id">{session.session_id}</td>
                  <td className="td-centered"><SessionStatusBadge endTime={session.end_time} /></td>
                  <td className={`cell-user-id td-centered${session.user_id == null ? ' cell-value-empty' : ''}`}>
                    {session.user_id == null ? EMPTY_CELL_DISPLAY : session.user_id}
                  </td>
                  <td className={`cell-risk cell-risk--${riskLevel} td-centered`}>
                    {session.average_risk_score.toFixed(2)}
                  </td>
                  <td className={`cell-timestamp td-centered-block${isIsoEmpty(session.start_time) ? ' cell-value-empty' : ''}`}>
                    {formatIsoLocal(session.start_time)}
                  </td>
                  <td className={`cell-timestamp td-centered-block${isIsoEmpty(session.end_time) ? ' cell-value-empty' : ''}`}>
                    {formatIsoLocal(session.end_time)}
                  </td>
                  <td className="cell-actions" onClick={(e) => e.stopPropagation()}>
                    {canDeleteSessions && isClosed && (
                      <button type="button" className="session-delete-btn" aria-label={`Delete session ${session.session_id}`} title="Delete session" onClick={(e) => handleDeleteClick(e, session)}>
                        <TrashIcon />
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
            {filteredSessions.length === 0 && sessions.length > 0 && (
              <tr><td colSpan={8} className="sessions-empty-state">No sessions match your search.</td></tr>
            )}
            {sessions.length === 0 && (
              <tr><td colSpan={8} className="sessions-empty-state">No sessions yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {canDeleteSessions && sessionToDelete && (
        <DeleteSessionModal
          sessionId={sessionToDelete.session_id}
          onConfirm={handleConfirmDelete}
          onCancel={() => setSessionToDelete(null)}
          isPending={deleteState?.isPending}
          error={deleteState?.error}
        />
      )}
    </>
  );
}
