import StyledSelect from '../ui/StyledSelect.jsx';

export default function SessionUserFilter({ value, onChange, users, disabled }) {
  const options = [
    { value: 'all', label: 'All users' },
    { value: 'admins', label: 'Admins only' },
    { value: 'users', label: 'Non-admins only' },
    ...(users.length > 0
      ? [
          { divider: true, value: '__divider__', label: '' },
          ...users.map((u) => ({
            value: String(u.user_id),
            label: `${u.username}${u.is_admin ? ' (admin)' : ''}`,
          })),
        ]
      : []),
  ];

  return (
    <StyledSelect
      className="styled-select--pill session-user-filter"
      value={value}
      onChange={onChange}
      options={options}
      disabled={disabled}
      ariaLabel="Filter sessions by user"
    />
  );
}
