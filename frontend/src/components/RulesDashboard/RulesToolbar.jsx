export default function RulesToolbar({
  searchTerm,
  onSearchChange,
  ruleType,
  onRuleTypeChange,
  computeClass,
  onComputeClassChange,
  hardBlock,
  onHardBlockChange,
  enabled,
  onEnabledChange,
  ruleTypes,
  computeClasses,
  disabled,
}) {
  return (
    <div className="rules-toolbar">
      <div className="rules-toolbar-row rules-toolbar-row--primary">
        <h1 className="sessions-title">Rules Dashboard</h1>
        <input
          type="search"
          className="session-search-input rules-search-input"
          placeholder="Search by rule code or description…"
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          disabled={disabled}
          aria-label="Search rules by code or description"
        />
      </div>
      <div className="rules-toolbar-row rules-toolbar-row--filters">
        <label className="rules-filter-field">
          <span className="rules-filter-label">Rule type</span>
          <select
            className="rules-filter-select"
            value={ruleType}
            onChange={(e) => onRuleTypeChange(e.target.value)}
            disabled={disabled}
          >
            <option value="">All types</option>
            {ruleTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="rules-filter-field">
          <span className="rules-filter-label">Compute class</span>
          <select
            className="rules-filter-select"
            value={computeClass}
            onChange={(e) => onComputeClassChange(e.target.value)}
            disabled={disabled}
          >
            <option value="">All classes</option>
            {computeClasses.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="rules-filter-field">
          <span className="rules-filter-label">Hard block</span>
          <select
            className="rules-filter-select"
            value={hardBlock}
            onChange={(e) => onHardBlockChange(e.target.value)}
            disabled={disabled}
          >
            <option value="all">All</option>
            <option value="yes">Hard block only</option>
            <option value="no">Not hard block</option>
          </select>
        </label>
        <label className="rules-filter-field">
          <span className="rules-filter-label">Enabled</span>
          <select
            className="rules-filter-select"
            value={enabled}
            onChange={(e) => onEnabledChange(e.target.value)}
            disabled={disabled}
          >
            <option value="all">All</option>
            <option value="yes">Enabled only</option>
            <option value="no">Disabled only</option>
          </select>
        </label>
      </div>
    </div>
  );
}
