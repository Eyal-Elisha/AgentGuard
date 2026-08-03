import { EMPTY_CELL_DISPLAY } from '../SessionsDashboard/sessionUtils.js';

export default function RuleRow({ rule, onToggleEnabled, pendingRuleCode }) {
  const hard = Boolean(rule.is_hard_block);
  const enabled = Boolean(rule.is_enabled);
  const rowClass = ['rules-row', hard ? 'rules-row--hard-block' : '', !enabled ? 'rules-row--disabled' : ''].filter(Boolean).join(' ');
  const desc = rule.description != null && String(rule.description).trim() !== '' ? rule.description : null;

  return (
    <tr className={rowClass}>
      <td className="rules-cell-code">{rule.rule_code}</td>
      <td className={`rules-cell-description${desc == null ? ' cell-value-empty' : ''}`}>{desc == null ? EMPTY_CELL_DISPLAY : desc}</td>
      <td className="rules-cell-mono rules-cell-rule-type">{rule.rule_type ?? EMPTY_CELL_DISPLAY}</td>
      <td className="rules-cell-mono rules-cell-compute">{rule.compute_class ?? EMPTY_CELL_DISPLAY}</td>
      <td>
        <span className={`rules-badge ${hard ? 'rules-badge--hard-block' : 'rules-badge--neutral'}`}>{hard ? 'Yes' : 'No'}</span>
      </td>
      <td>
        <button
          type="button"
          className={`rules-switch ${enabled ? 'rules-switch--on' : 'rules-switch--off'} ${pendingRuleCode === rule.rule_code ? 'rules-switch--pending' : ''}`}
          onClick={() => onToggleEnabled(rule.rule_code, !enabled)}
          disabled={pendingRuleCode === rule.rule_code}
          role="switch" aria-checked={enabled}
        >
          <span className="rules-switch-track" aria-hidden="true"><span className="rules-switch-thumb" /></span>
          <span className="rules-switch-label">{enabled ? 'Yes' : 'No'}</span>
        </button>
      </td>
    </tr>
  );
}
