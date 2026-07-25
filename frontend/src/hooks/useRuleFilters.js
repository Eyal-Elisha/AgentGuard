import { useMemo, useState } from 'react';

export function useRuleFilters(rules) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRuleType, setFilterRuleType] = useState('');
  const [filterComputeClass, setFilterComputeClass] = useState('');
  const [filterHardBlock, setFilterHardBlock] = useState('');
  const [filterEnabled, setFilterEnabled] = useState('');

  const ruleTypes = useMemo(() => {
    const set = new Set();
    for (const r of rules) if (r.rule_type) set.add(r.rule_type);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [rules]);

  const computeClasses = useMemo(() => {
    const set = new Set();
    for (const r of rules) if (r.compute_class) set.add(r.compute_class);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [rules]);

  const filteredRules = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return rules.filter((rule) => {
      if (q) {
        const codeMatch = rule.rule_code.toLowerCase().includes(q);
        const desc = rule.description != null ? String(rule.description).toLowerCase() : '';
        if (!codeMatch && !desc.includes(q)) return false;
      }
      if (filterRuleType && rule.rule_type !== filterRuleType) return false;
      if (filterComputeClass && rule.compute_class !== filterComputeClass) return false;
      if (filterHardBlock === 'yes' && !rule.is_hard_block) return false;
      if (filterHardBlock === 'no' && rule.is_hard_block) return false;
      if (filterEnabled === 'yes' && !rule.is_enabled) return false;
      if (filterEnabled === 'no' && rule.is_enabled) return false;
      return true;
    });
  }, [rules, searchTerm, filterRuleType, filterComputeClass, filterHardBlock, filterEnabled]);

  return {
    searchTerm, setSearchTerm,
    filterRuleType, setFilterRuleType,
    filterComputeClass, setFilterComputeClass,
    filterHardBlock, setFilterHardBlock,
    filterEnabled, setFilterEnabled,
    ruleTypes, computeClasses, filteredRules
  };
}
