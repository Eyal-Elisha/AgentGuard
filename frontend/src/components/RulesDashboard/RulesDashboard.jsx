import { useState } from 'react';
import { createEnableRuleHandler } from './functions/EnableRule.js';
import RulesTable from './RulesTable.jsx';
import RulesToolbar from './RulesToolbar.jsx';
import CustomBlacklist from './CustomBlacklist.jsx';
import { useAuth } from '../../context/AuthContext.jsx';
import { useRules, normalizeRule } from '../../hooks/useRules.js';
import { useRuleFilters } from '../../hooks/useRuleFilters.js';
import '../SessionsDashboard/SessionsDashboard.css';
import './RulesDashboard.css';

export default function RulesDashboard() {
  const { currentUser } = useAuth();
  const { rules, setRules, isLoading, error, setError } = useRules();
  const filters = useRuleFilters(rules);
  const [pendingRuleCode, setPendingRuleCode] = useState(null);

  const handleScrollToBlacklist = () => {
    document.getElementById('custom-blacklist-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleToggleEnabled = createEnableRuleHandler({
    setPendingRuleCode, setRules, setError, normalizeRule,
  });

  const showTable = !isLoading && !error;

  return (
    <div className="sessions-page">
      <main className="sessions-dashboard-main">
        <div className="sessions-dashboard-card rules-dashboard-card">
          <RulesToolbar
            {...filters}
            onSearchChange={filters.setSearchTerm}
            onRuleTypeChange={filters.setFilterRuleType}
            onComputeClassChange={filters.setFilterComputeClass}
            onHardBlockChange={filters.setFilterHardBlock}
            onEnabledChange={filters.setFilterEnabled}
            disabled={!showTable}
            showManageBlacklist={currentUser?.isAdmin}
            onManageBlacklist={handleScrollToBlacklist}
          />

          {isLoading && <div className="sessions-loading" role="status">Loading rules…</div>}
          {error && <div className="sessions-error-alert" role="alert">{error}</div>}

          {showTable && (
            <RulesTable
              filteredRules={filters.filteredRules}
              rules={rules}
              onToggleEnabled={handleToggleEnabled}
              pendingRuleCode={pendingRuleCode}
            />
          )}

          <CustomBlacklist />
        </div>
      </main>
    </div>
  );
}
