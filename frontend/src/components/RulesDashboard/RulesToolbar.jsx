import RulesToolbarFilters from './RulesToolbarFilters.jsx';

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
  showManageBlacklist,
  onManageBlacklist,
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
          style={{ maxWidth: '300px' }}
        />
      </div>
      <RulesToolbarFilters
        ruleType={ruleType}
        onRuleTypeChange={onRuleTypeChange}
        computeClass={computeClass}
        onComputeClassChange={onComputeClassChange}
        hardBlock={hardBlock}
        onHardBlockChange={onHardBlockChange}
        enabled={enabled}
        onEnabledChange={onEnabledChange}
        ruleTypes={ruleTypes}
        computeClasses={computeClasses}
        disabled={disabled}
        showManageBlacklist={showManageBlacklist}
        onManageBlacklist={onManageBlacklist}
      />
    </div>
  );
}
