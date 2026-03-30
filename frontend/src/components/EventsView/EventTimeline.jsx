import { useEffect, useState } from 'react';
import { formatIsoLocal } from '../SessionsDashboard/sessionUtils.js';

const ACTION_CLASS_MAP = {
  Block: 'event-action--block',
  Warn: 'event-action--warn',
  Allow: 'event-action--allow',
};

async function copyTextToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const el = document.createElement('textarea');
      el.value = text;
      el.setAttribute('readonly', '');
      el.style.position = 'fixed';
      el.style.left = '-9999px';
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      return true;
    } catch {
      return false;
    }
  }
}

export default function EventTimeline({
  events,
  selectedEventId,
  onSelectEvent,
}) {
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (toast == null) return undefined;
    const t = window.setTimeout(() => setToast(null), 1100);
    return () => window.clearTimeout(t);
  }, [toast]);

  return (
    <section className="events-timeline-pane">
      <h2 className="events-pane-title">Event Timeline</h2>
      <div className="events-timeline-list">
        {events.map((event, index) => {
          const actionClass = ACTION_CLASS_MAP[event.guard_action] ?? '';
          const isSelected = event.event_id === selectedEventId;
          return (
            <button
              key={event.event_id}
              type="button"
              className={`events-timeline-item ${actionClass} ${isSelected ? 'events-timeline-item--selected' : ''}`}
              onClick={() => onSelectEvent(event.event_id)}
              aria-pressed={isSelected}
            >
              <span className="events-corner-id" aria-hidden="true">#{event.event_id}</span>
              <span className={`events-timeline-dot ${actionClass}`} />
              {index < events.length - 1 && <span className="events-timeline-line" />}
              <div className="events-timeline-content">
                <div className="events-timeline-row">
                  <div className="events-timeline-meta">
                    <span className="events-timestamp">{formatIsoLocal(event.timestamp)}</span>
                  </div>
                  <span className={`events-action-badge ${actionClass}`}>
                    {event.guard_action.toUpperCase()}
                  </span>
                </div>
                <div className="events-url-row">
                  <span
                    className="events-url-text events-url-copy"
                    role="button"
                    tabIndex={0}
                    title="Click to copy URL"
                    aria-label={`Copy URL for event ${event.event_id}`}
                    onClick={async (e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      const ok = await copyTextToClipboard(event.url);
                      setToast(ok ? 'Copied URL to clipboard' : 'Failed to copy URL');
                    }}
                    onKeyDown={async (e) => {
                      if (e.key !== 'Enter' && e.key !== ' ') return;
                      e.preventDefault();
                      e.stopPropagation();
                      const ok = await copyTextToClipboard(event.url);
                      setToast(ok ? 'Copied URL to clipboard' : 'Failed to copy URL');
                    }}
                  >
                    {event.url}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
      {toast && (
        <div className="events-toast" role="status" aria-live="polite">
          {toast}
        </div>
      )}
    </section>
  );
}
