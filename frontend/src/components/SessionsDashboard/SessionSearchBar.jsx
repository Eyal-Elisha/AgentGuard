export default function SessionSearchBar({
  searchTerm,
  onSearchChange,
  disabled,
}) {
  return (
    <input
      type="text"
      className="session-search-input"
      placeholder="Search Session..."
      value={searchTerm}
      onChange={(event) => onSearchChange(event.target.value)}
      disabled={disabled}
    />
  );
}
