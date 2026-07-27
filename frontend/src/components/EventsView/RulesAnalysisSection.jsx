import { useId, useState } from 'react';
import RulesAnalysisTable from './RulesAnalysisTable.jsx';

export default function RulesAnalysisSection({ section, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  const count = section.rows.length;
  const countLabel = `${count} ${count === 1 ? 'rule' : 'rules'}`;

  return (
    <section className="events-rules-type-block">
      <div className="events-rules-type-header">
        <button
          type="button"
          className="events-rules-type-toggle"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((o) => !o)}
        >
          <span aria-hidden="true">{open ? '▾' : '▸'}</span>
          <span className="events-rules-type-toggle-label">{section.label}</span>
        </button>
        <span className="events-pane-pill">{countLabel}</span>
      </div>
      {open && (
        <div id={panelId}>
          <RulesAnalysisTable rows={section.rows} />
        </div>
      )}
    </section>
  );
}
