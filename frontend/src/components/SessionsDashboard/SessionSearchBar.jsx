export default function SessionSearchBar({
  searchTerm,
  onSearchChange,
  disabled,
}) {
  return (
    <div className="sessions-dashboard-card-header">
      <h1 className="sessions-title">Sessions Dashboard</h1>
      <input
        type="text"
        className="session-search-input"
        placeholder="Search Session..."
        value={searchTerm}
        onChange={(event) => onSearchChange(event.target.value)}
        disabled={disabled}
      />
    </div>
  );
}
