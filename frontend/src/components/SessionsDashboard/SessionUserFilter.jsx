export default function SessionUserFilter({ value, onChange, users, disabled }) {
  return (
    <select
      className="session-user-filter"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      aria-label="Filter sessions by user"
    >
      <option value="all">All users</option>
      <option value="admins">Admins only</option>
      <option value="users">Non-admins only</option>
      {users.length > 0 && <option disabled>──────────</option>}
      {users.map((u) => (
        <option key={u.user_id} value={String(u.user_id)}>
          {u.username}{u.is_admin ? ' (admin)' : ''}
        </option>
      ))}
    </select>
  );
}
