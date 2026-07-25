import { useEffect, useId, useRef } from 'react';
import { HELP_COPY } from '../../content/helpCopy.js';
import { useTour } from '../../onboarding/TourProvider.jsx';
import './HelpDrawer.css';

export default function HelpDrawer({ id, open, onClose }) {
  const { startTour } = useTour();
  const titleId = useId();
  const closeRef = useRef(null);
  const tourStartTimerRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    closeRef.current?.focus();
    function onKey(e) {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  useEffect(() => () => {
    if (tourStartTimerRef.current != null) {
      window.clearTimeout(tourStartTimerRef.current);
      tourStartTimerRef.current = null;
    }
  }, []);

  if (!open) return null;

  function handleStartTour() {
    onClose();
    if (tourStartTimerRef.current != null) {
      window.clearTimeout(tourStartTimerRef.current);
    }
    tourStartTimerRef.current = window.setTimeout(() => {
      tourStartTimerRef.current = null;
      startTour();
    }, 120);
  }

  return (
    <div className="help-drawer-root" role="presentation">
      <button type="button" className="help-drawer-backdrop" aria-label="Close help" onClick={onClose} />
      <aside
        id={id}
        className="help-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="help-drawer-header">
          <h2 id={titleId} className="help-drawer-title">{HELP_COPY.title}</h2>
          <button
            ref={closeRef}
            type="button"
            className="help-drawer-close"
            onClick={onClose}
            aria-label={HELP_COPY.closeLabel}
          >
            ×
          </button>
        </div>

        <div className="help-drawer-body">
          {HELP_COPY.blurb.map((p) => (
            <p key={p} className="help-drawer-blurb">{p}</p>
          ))}

          <button type="button" className="help-drawer-tour-btn" onClick={handleStartTour}>
            {HELP_COPY.tourButtonLabel}
          </button>
        </div>
      </aside>
    </div>
  );
}
