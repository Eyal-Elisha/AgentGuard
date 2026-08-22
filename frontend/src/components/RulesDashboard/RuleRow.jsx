import { EMPTY_CELL_DISPLAY } from '../SessionsDashboard/sessionUtils.js';

function ToggleSwitch({ on, pending, onChange, label, title, variant = '' }) {
  return (
    <button
      type="button"
      className={[
        'rules-switch',
        on ? 'rules-switch--on' : 'rules-switch--off',
        pending ? 'rules-switch--pending' : '',
        variant,
      ].filter(Boolean).join(' ')}
      onClick={() => onChange(!on)}
      disabled={pending}
      role="switch"
      aria-checked={on}
      aria-label={label}
      title={title}
    >
      <span className="rules-switch-track" aria-hidden="true"><span className="rules-switch-thumb" /></span>
      <span className="rules-switch-label">{on ? 'Yes' : 'No'}</span>
    </button>
  );
}

export default function RuleRow({
  rule,
  onToggleEnabled,
  onToggleHardBlock,
  pendingRuleCode,
  canEditHardBlock = false,
}) {
  const hard = Boolean(rule.is_hard_block);
  const enabled = Boolean(rule.is_enabled);
  const pending = pendingRuleCode === rule.rule_code;
  const rowClass = ['rules-row', hard ? 'rules-row--hard-block' : '', !enabled ? 'rules-row--disabled' : ''].filter(Boolean).join(' ');
  const desc = rule.description != null && String(rule.description).trim() !== '' ? rule.description : null;

  return (
    <tr className={rowClass}>
      <td className="rules-cell-code">{rule.rule_code}</td>
      <td className={`rules-cell-description${desc == null ? ' cell-value-empty' : ''}`}>{desc == null ? EMPTY_CELL_DISPLAY : desc}</td>
      <td className="rules-cell-mono rules-cell-rule-type">{rule.rule_type ?? EMPTY_CELL_DISPLAY}</td>
      <td className="rules-cell-mono rules-cell-compute">{rule.compute_class ?? EMPTY_CELL_DISPLAY}</td>
      <td>
        {/* Only an admin may hand a rule the power to override every other
            signal, so everyone else keeps the read-only badge. */}
        {canEditHardBlock ? (
          <ToggleSwitch
            on={hard}
            pending={pending}
            onChange={(next) => onToggleHardBlock(rule.rule_code, next)}
            label={`Hard block for ${rule.rule_code}`}
            title="A hard-blocking rule forces a Block on its own, whatever the other rules say"
            variant="rules-switch--danger"
          />
        ) : (
          <span className={`rules-badge ${hard ? 'rules-badge--hard-block' : 'rules-badge--neutral'}`}>{hard ? 'Yes' : 'No'}</span>
        )}
      </td>
      <td>
        <ToggleSwitch
          on={enabled}
          pending={pending}
          onChange={(next) => onToggleEnabled(rule.rule_code, next)}
          label={`Enabled for ${rule.rule_code}`}
        />
      </td>
    </tr>
  );
}
