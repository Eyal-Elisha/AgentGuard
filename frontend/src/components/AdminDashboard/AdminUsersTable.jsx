import { useState } from 'react';
import { useAuth } from '../../context/AuthContext.jsx';

export default function AdminUsersTable({ users, onPromote }) {
  const { currentUser } = useAuth();
  const [pendingUserId, setPendingUserId] = useState(null);
  const [actionError, setActionError] = useState(null);

  async function handlePromote(userId) {
    if (!onPromote) return;
    setActionError(null);
    setPendingUserId(userId);
    try {
      const err = await onPromote(userId);
      if (err) setActionError(err);
    } finally {
      setPendingUserId(null);
    }
  }

  return (
    <div className="admin-table-wrap">
      {actionError && <div className="sessions-error-alert" role="alert">{actionError}</div>}
      <table className="sessions-table admin-users-table">
        <thead>
          <tr>
            <th>User ID</th>
            <th>Username</th>
            <th>Role</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const isSelf = String(currentUser?.userId) === String(user.user_id);
            const isPending = pendingUserId === user.user_id;
            return (
              <tr key={user.user_id} className="admin-users-row">
                <td>{user.user_id}</td>
                <td style={{ fontWeight: 600 }}>{user.username}</td>
                <td>
                  <span className={`admin-role-badge ${user.is_admin ? 'admin-role-badge--admin' : 'admin-role-badge--user'}`}>
                    {user.is_admin ? 'Admin' : 'User'}
                  </span>
                </td>
                <td className="admin-actions-cell">
                  {!user.is_admin && (
                    <button
                      type="button"
                      className="admin-promote-btn"
                      onClick={() => handlePromote(user.user_id)}
                      disabled={isPending || isSelf}
                      title={isSelf ? "You can't promote yourself" : 'Promote to admin'}
                    >
                      {isPending ? 'Promoting…' : 'Promote to admin'}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
          {users.length === 0 && (
            <tr>
              <td colSpan={4} className="sessions-empty-state">
                No users found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
