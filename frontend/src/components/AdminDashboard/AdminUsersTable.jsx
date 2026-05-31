export default function AdminUsersTable({ users }) {
  return (
    <div className="admin-table-wrap">
      <table className="sessions-table">
        <thead>
          <tr>
            <th>User ID</th>
            <th>Username</th>
            <th>Role</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.user_id} className="sessions-row">
              <td>{user.user_id}</td>
              <td style={{ fontWeight: 600 }}>{user.username}</td>
              <td>
                <span style={{
                  padding: '0.15rem 0.5rem',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  background: user.is_admin ? 'color-mix(in srgb, var(--color-brand) 15%, transparent)' : 'color-mix(in srgb, var(--color-text-muted) 15%, transparent)',
                  color: user.is_admin ? 'var(--color-brand)' : 'var(--color-text-muted)',
                }}>
                  {user.is_admin ? 'Admin' : 'User'}
                </span>
              </td>
            </tr>
          ))}
          {users.length === 0 && (
            <tr>
              <td colSpan={3} className="sessions-empty-state">
                No users found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
