import { useState } from 'react';
import { createEnableRuleHandler } from './functions/EnableRule.js';
import { createHardBlockRuleHandler } from './functions/HardBlockRule.js';
import RulesTable from './RulesTable.jsx';
import RulesToolbar from './RulesToolbar.jsx';
import { useRules, normalizeRule } from '../../hooks/useRules.js';
import { useRuleFilters } from '../../hooks/useRuleFilters.js';
import { useAuth } from '../../context/AuthContext.jsx';
import '../SessionsDashboard/SessionsDashboard.css';
import './RulesDashboard.css';

export default function RulesDashboard() {
  const { currentUser } = useAuth();
  const { rules, setRules, isLoading, error, setError } = useRules();
  const filters = useRuleFilters(rules);
  const [pendingRuleCode, setPendingRuleCode] = useState(null);

  const handleToggleEnabled = createEnableRuleHandler({
    setPendingRuleCode, setRules, setError, normalizeRule,
  });

  // The endpoint is admin-only; hiding the switch keeps a non-admin from
  // clicking something that can only ever answer 403.
  const canEditHardBlock = Boolean(currentUser?.isAdmin);
  const handleToggleHardBlock = createHardBlockRuleHandler({
    setPendingRuleCode, setRules, setError, normalizeRule,
  });

  const showTable = !isLoading && !error;

  return (
    <div className="sessions-page">
      <main className="sessions-dashboard-main">
        <div className="sessions-dashboard-card rules-dashboard-card">
          <div data-tour="rules-main">
            <RulesToolbar
              searchTerm={filters.searchTerm}
              onSearchChange={filters.setSearchTerm}
              ruleType={filters.filterRuleType}
              onRuleTypeChange={filters.setFilterRuleType}
              computeClass={filters.filterComputeClass}
              onComputeClassChange={filters.setFilterComputeClass}
              hardBlock={filters.filterHardBlock}
              onHardBlockChange={filters.setFilterHardBlock}
              enabled={filters.filterEnabled}
              onEnabledChange={filters.setFilterEnabled}
              ruleTypes={filters.ruleTypes}
              computeClasses={filters.computeClasses}
              disabled={!showTable}
              showManageBlacklist={false}
            />
          </div>

          {isLoading && <div className="sessions-loading" role="status">Loading rules…</div>}
          {error && <div className="sessions-error-alert" role="alert">{error}</div>}

          {showTable && (
            <RulesTable
              filteredRules={filters.filteredRules}
              rules={rules}
              onToggleEnabled={handleToggleEnabled}
              onToggleHardBlock={handleToggleHardBlock}
              pendingRuleCode={pendingRuleCode}
              canEditHardBlock={canEditHardBlock}
            />
          )}
        </div>
      </main>
    </div>
  );
}
