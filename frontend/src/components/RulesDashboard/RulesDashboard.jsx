import { useEffect, useMemo, useState } from 'react';
import { getApiBaseUrl, apiFetchHeaders } from '../../api/client.js';
import { readErrorMessage } from '../SessionsDashboard/sessionUtils.js';
import RulesTable from './RulesTable.jsx';
import RulesToolbar from './RulesToolbar.jsx';
import '../SessionsDashboard/SessionsDashboard.css';
import './RulesDashboard.css';

function normalizeRule(raw) {
  return {
    rule_code: raw.rule_code != null ? String(raw.rule_code) : '',
    description: raw.description ?? null,
    rule_type: raw.rule_type != null ? String(raw.rule_type) : '',
    compute_class: raw.compute_class != null ? String(raw.compute_class) : '',
    weight: typeof raw.weight === 'number' ? raw.weight : Number(raw.weight),
    is_hard_block: Boolean(raw.is_hard_block),
    is_enabled: Boolean(raw.is_enabled),
  };
}

export default function RulesDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRuleType, setFilterRuleType] = useState('');
  const [filterComputeClass, setFilterComputeClass] = useState('');
  const [filterHardBlock, setFilterHardBlock] = useState('all');
  const [filterEnabled, setFilterEnabled] = useState('all');
  const [rules, setRules] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadRules() {
      const baseUrl = getApiBaseUrl();
      if (baseUrl == null) {
        if (!cancelled) {
          setError(
            'API base URL is not configured. Set VITE_API_BASE_URL in your .env file.',
          );
          setIsLoading(false);
        }
        return;
      }

      const url = `${baseUrl}/rules`;

      try {
        const response = await fetch(url, { headers: apiFetchHeaders() });

        if (!response.ok) {
          const message = await readErrorMessage(response, 'rules');
          if (!cancelled) {
            setRules([]);
            setError(message);
          }
          return;
        }

        const data = await response.json();
        if (!Array.isArray(data)) {
          if (!cancelled) {
            setRules([]);
            setError('Received an unexpected response from the server.');
          }
          return;
        }

        if (!cancelled) {
          setRules(data.map(normalizeRule));
          setError(null);
        }
      } catch {
        if (!cancelled) {
          setRules([]);
          setError(
            'Unable to reach the server. Check your connection and that the API is running.',
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadRules();
    return () => {
      cancelled = true;
    };
  }, []);

  const ruleTypes = useMemo(() => {
    const set = new Set();
    for (const r of rules) {
      if (r.rule_type) set.add(r.rule_type);
    }
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [rules]);

  const computeClasses = useMemo(() => {
    const set = new Set();
    for (const r of rules) {
      if (r.compute_class) set.add(r.compute_class);
    }
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [rules]);

  const filteredRules = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return rules.filter((rule) => {
      if (q) {
        const codeMatch = rule.rule_code.toLowerCase().includes(q);
        const desc =
          rule.description != null ? String(rule.description).toLowerCase() : '';
        const descMatch = desc.includes(q);
        if (!codeMatch && !descMatch) return false;
      }
      if (filterRuleType && rule.rule_type !== filterRuleType) return false;
      if (filterComputeClass && rule.compute_class !== filterComputeClass) {
        return false;
      }
      if (filterHardBlock === 'yes' && !rule.is_hard_block) return false;
      if (filterHardBlock === 'no' && rule.is_hard_block) return false;
      if (filterEnabled === 'yes' && !rule.is_enabled) return false;
      if (filterEnabled === 'no' && rule.is_enabled) return false;
      return true;
    });
  }, [
    rules,
    searchTerm,
    filterRuleType,
    filterComputeClass,
    filterHardBlock,
    filterEnabled,
  ]);

  const showTable = !isLoading && !error;

  return (
    <div className="sessions-page">
      <main className="sessions-dashboard-main">
        <div className="sessions-dashboard-card rules-dashboard-card">
          <RulesToolbar
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            ruleType={filterRuleType}
            onRuleTypeChange={setFilterRuleType}
            computeClass={filterComputeClass}
            onComputeClassChange={setFilterComputeClass}
            hardBlock={filterHardBlock}
            onHardBlockChange={setFilterHardBlock}
            enabled={filterEnabled}
            onEnabledChange={setFilterEnabled}
            ruleTypes={ruleTypes}
            computeClasses={computeClasses}
            disabled={!showTable}
          />

          {isLoading && (
            <div className="sessions-loading" role="status" aria-live="polite">
              Loading rules…
            </div>
          )}

          {error && (
            <div className="sessions-error-alert" role="alert">
              {error}
            </div>
          )}

          {showTable && (
            <RulesTable filteredRules={filteredRules} rules={rules} />
          )}
        </div>
      </main>
    </div>
  );
}
