import { requestRuleEnabledUpdate } from '../../../api/rules/enableRule.js';

function applyEnabledState(ruleCode, isEnabled, setRules) {
  setRules((current) =>
    current.map((rule) =>
      rule.rule_code === ruleCode
        ? { ...rule, is_enabled: isEnabled }
        : rule,
    ),
  );
}

export function createEnableRuleHandler({
  setPendingRuleCode,
  setRules,
  setError,
  normalizeRule,
}) {
  return async function handleToggleEnabled(ruleCode, nextEnabled) {
    setPendingRuleCode(ruleCode);
    applyEnabledState(ruleCode, nextEnabled, setRules);

    try {
      const updatedRule = normalizeRule(
        await requestRuleEnabledUpdate(ruleCode, nextEnabled),
      );
      applyEnabledState(updatedRule.rule_code, updatedRule.is_enabled, setRules);
      setError(null);
    } catch (err) {
      applyEnabledState(ruleCode, !nextEnabled, setRules);
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to update the rule state.',
      );
    } finally {
      setPendingRuleCode(null);
    }
  };
}
