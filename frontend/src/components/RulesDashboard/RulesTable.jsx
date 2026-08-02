import RuleRow from './RuleRow.jsx';

export default function RulesTable({ filteredRules, rules, onToggleEnabled, pendingRuleCode }) {
  return (
    <div className="rules-table-wrapper">
      <div className="rules-table-scroll">
        <table className="rules-table">
          <thead>
            <tr>
              <th>RULE CODE</th>
              <th className="rules-th-description">DESCRIPTION</th>
              <th>RULE TYPE</th>
              <th className="rules-th-compute">COMPUTE CLASS</th>
              <th>HARD BLOCK</th>
              <th>ENABLED</th>
            </tr>
          </thead>
          <tbody>
            {filteredRules.map((rule) => (
              <RuleRow
                key={rule.rule_code}
                rule={rule}
                onToggleEnabled={onToggleEnabled}
                pendingRuleCode={pendingRuleCode}
              />
            ))}
            {rules.length > 0 && filteredRules.length === 0 && (
              <tr className="rules-empty-row">
                <td colSpan={6} className="rules-empty-state">No rules match your search or filters.</td>
              </tr>
            )}
            {rules.length === 0 && (
              <tr className="rules-empty-row">
                <td colSpan={6} className="rules-empty-state">No rules configured yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
