import { useEffect, useId, useRef, useState } from 'react';

function RuleScoreBar({ score }) {
  const pct = typeof score === 'number' ? Math.min(Math.max(score * 100, 0), 100) : 0;
  const hue = Math.round(120 - pct * 1.2); // green→red
  return (
    <div className="rule-score-bar-wrap" title={`${pct.toFixed(0)}%`}>
      <div className="rule-score-bar-track">
        <div className="rule-score-bar-fill" style={{ width: `${pct}%`, background: `hsl(${hue}, 70%, 52%)` }} />
      </div>
      <span className="rule-score-bar-label">{typeof score === 'number' ? score.toFixed(2) : '–'}</span>
    </div>
  );
}

function RuleDetailsInfo({ details }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const tipId = useId();

  useEffect(() => {
    if (!open) return undefined;

    function onPointerDown(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
      }
    }

    function onKeyDown(e) {
      if (e.key === 'Escape') setOpen(false);
    }

    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <span
      ref={wrapRef}
      className={`events-rules-details-info${open ? ' events-rules-details-info--open' : ''}`}
    >
      <button
        type="button"
        className="events-rules-details-info-btn"
        aria-label="Rule details"
        aria-expanded={open}
        aria-describedby={tipId}
        onClick={() => setOpen((v) => !v)}
      >
        i
      </button>
      <span id={tipId} role="tooltip" className="events-rules-details-tip">
        {details}
      </span>
    </span>
  );
}

export default function RulesAnalysisTable({ rows }) {
  return (
    <div className="events-rules-table-wrap">
      <table className="sessions-table events-rules-table">
        <thead>
          <tr>
            <th>RULE CODE</th>
            <th className="th-centered">WEIGHT</th>
            <th className="th-centered">HARD BLOCK</th>
            <th className="th-centered">RULE SCORE</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const hard = Boolean(row.is_hard_block ?? row.hard_block);
            const detailsText = typeof row.details === 'string' ? row.details.trim() : '';
            const hasDetails = detailsText.length > 0;
            return (
              <tr key={row.analysis_id} className="sessions-row">
                <td>
                  <span className="events-rules-code-cell">
                    {hasDetails && <RuleDetailsInfo details={detailsText} />}
                    <span className="events-rules-code">{row.rule_code}</span>
                  </span>
                </td>
                <td className="td-centered">{row.weight != null ? row.weight : '–'}</td>
                <td className="td-centered">
                  <span className={`rules-badge ${hard ? 'rules-badge--hard-block' : 'rules-badge--neutral'}`}>
                    {hard ? 'Yes' : 'No'}
                  </span>
                </td>
                <td className="td-centered"><RuleScoreBar score={row.rule_score} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
