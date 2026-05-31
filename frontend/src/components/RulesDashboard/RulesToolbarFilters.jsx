import FilterSelect from './FilterSelect.jsx';

export default function RulesToolbarFilters({
  ruleType, onRuleTypeChange,
  computeClass, onComputeClassChange,
  hardBlock, onHardBlockChange,
  enabled, onEnabledChange,
  ruleTypes, computeClasses,
  disabled, showManageBlacklist, onManageBlacklist,
}) {
  return (
    <div className="rules-toolbar-row rules-toolbar-row--filters" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
      <FilterSelect 
        label="Rule type" value={ruleType} onChange={onRuleTypeChange} 
        options={ruleTypes} disabled={disabled} allLabel="All types" 
      />
      <FilterSelect 
        label="Compute class" value={computeClass} onChange={onComputeClassChange} 
        options={computeClasses} disabled={disabled} allLabel="All classes" 
      />
      <FilterSelect 
        label="Hard block" value={hardBlock} onChange={onHardBlockChange} 
        options={[{value: 'all', label: 'All'}, {value: 'yes', label: 'Hard block only'}, {value: 'no', label: 'Not hard block'}]} 
        disabled={disabled} 
      />
      <FilterSelect 
        label="Enabled" value={enabled} onChange={onEnabledChange} 
        options={[{value: 'all', label: 'All'}, {value: 'yes', label: 'Enabled only'}, {value: 'no', label: 'Disabled only'}]} 
        disabled={disabled} 
      />

      {showManageBlacklist && (
        <div className="rules-filter-field" style={{ marginLeft: 'auto' }}>
          <span className="rules-filter-label" style={{ visibility: 'hidden' }}>Action</span>
          <button 
            type="button" onClick={onManageBlacklist} className="rules-filter-select"
            style={{
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              gap: '0.5rem', fontWeight: '500', color: 'var(--color-text-primary)',
              transition: 'border-color 0.2s ease, background-color 0.2s ease'
            }}
            onMouseOver={(e) => { e.currentTarget.style.borderColor = 'var(--color-brand)'; }}
            onMouseOut={(e) => { e.currentTarget.style.borderColor = 'var(--color-border-subtle)'; }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M15 9l-6 6"/><path d="M9 9l6 6"/>
            </svg>
            Manage Blacklist
          </button>
        </div>
      )}
    </div>
  );
}
