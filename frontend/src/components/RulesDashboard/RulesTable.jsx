import { EMPTY_CELL_DISPLAY } from '../SessionsDashboard/sessionUtils.js';

function formatWeight(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return EMPTY_CELL_DISPLAY;
  const s = String(value);
  if (s.includes('e') || s.includes('E')) return value.toFixed(4);
  const rounded = Math.round(value * 10000) / 10000;
  return String(rounded);
}

export default function RulesTable({
  filteredRules,
  rules,
  onToggleEnabled,
  pendingRuleCode,
}) {
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
              <th>WEIGHT</th>
              <th>HARD BLOCK</th>
              <th>ENABLED</th>
            </tr>
          </thead>
          <tbody>
            {filteredRules.map((rule) => {
              const hard = Boolean(rule.is_hard_block);
              const enabled = Boolean(rule.is_enabled);
              const rowClass = [
                'rules-row',
                hard ? 'rules-row--hard-block' : '',
                !enabled ? 'rules-row--disabled' : '',
              ]
                .filter(Boolean)
                .join(' ');
              const desc =
                rule.description != null && String(rule.description).trim() !== ''
                  ? rule.description
                  : null;
              return (
                <tr key={rule.rule_code} className={rowClass}>
                  <td className="rules-cell-code">{rule.rule_code}</td>
                  <td
                    className={`rules-cell-description${desc == null ? ' cell-value-empty' : ''}`}
                  >
                    {desc == null ? EMPTY_CELL_DISPLAY : desc}
                  </td>
                  <td className="rules-cell-mono rules-cell-rule-type">
                    {rule.rule_type ?? EMPTY_CELL_DISPLAY}
                  </td>
                  <td className="rules-cell-mono rules-cell-compute">
                    {rule.compute_class ?? EMPTY_CELL_DISPLAY}
                  </td>
                  <td className="rules-cell-mono rules-cell-numeric">
                    {formatWeight(rule.weight)}
                  </td>
                  <td>
                    <span
                      className={`rules-badge ${hard ? 'rules-badge--hard-block' : 'rules-badge--neutral'}`}
                    >
                      {hard ? 'Yes' : 'No'}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className={`rules-switch ${enabled ? 'rules-switch--on' : 'rules-switch--off'} ${pendingRuleCode === rule.rule_code ? 'rules-switch--pending' : ''}`}
                      onClick={() => onToggleEnabled(rule.rule_code, !enabled)}
                      disabled={pendingRuleCode === rule.rule_code}
                      role="switch"
                      aria-checked={enabled}
                      aria-label={`${enabled ? 'Disable' : 'Enable'} ${rule.rule_code}`}
                      aria-busy={pendingRuleCode === rule.rule_code}
                    >
                      <span className="rules-switch-track" aria-hidden="true">
                        <span className="rules-switch-thumb" />
                      </span>
                      <span className="rules-switch-label">
                        {enabled ? 'Yes' : 'No'}
                      </span>
                    </button>
                  </td>
                </tr>
              );
            })}
            {rules.length > 0 && filteredRules.length === 0 && (
              <tr className="rules-empty-row">
                <td colSpan={7} className="rules-empty-state">
                  No rules match your search or filters.
                </td>
              </tr>
            )}
            {rules.length === 0 && (
              <tr className="rules-empty-row">
                <td colSpan={7} className="rules-empty-state">
                  No rules configured yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
