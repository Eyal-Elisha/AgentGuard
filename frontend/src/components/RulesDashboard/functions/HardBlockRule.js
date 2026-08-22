import { requestRuleHardBlockUpdate } from '../../../api/rules/hardBlockRule.js';

function applyHardBlockState(ruleCode, isHardBlock, setRules) {
  setRules((current) =>
    current.map((rule) =>
      rule.rule_code === ruleCode
        ? { ...rule, is_hard_block: isHardBlock }
        : rule,
    ),
  );
}

export function createHardBlockRuleHandler({
  setPendingRuleCode,
  setRules,
  setError,
  normalizeRule,
}) {
  return async function handleToggleHardBlock(ruleCode, nextHardBlock) {
    setPendingRuleCode(ruleCode);
    // Move the switch straight away; the server is the authority, so the
    // response overwrites this and a failure puts it back.
    applyHardBlockState(ruleCode, nextHardBlock, setRules);

    try {
      const updatedRule = normalizeRule(
        await requestRuleHardBlockUpdate(ruleCode, nextHardBlock),
      );
      applyHardBlockState(updatedRule.rule_code, updatedRule.is_hard_block, setRules);
      setError(null);
    } catch (err) {
      applyHardBlockState(ruleCode, !nextHardBlock, setRules);
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
