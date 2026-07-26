import { formatDateTime } from '../SessionsDashboard/sessionUtils.js';

const ACTION_CLASS_MAP = { Block: 'event-action--block', Warn: 'event-action--warn', Allow: 'event-action--allow' };

async function copyTextToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const el = document.createElement('textarea');
      el.value = text; el.setAttribute('readonly', ''); el.style.position = 'fixed'; el.style.left = '-9999px';
      document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el);
      return true;
    } catch { return false; }
  }
}

export default function EventTimelineItem({ event, isSelected, isLast, onSelect, onToast }) {
  const actionClass = ACTION_CLASS_MAP[event.guard_action] ?? '';
  const handleCopy = async (e) => {
    e.preventDefault(); e.stopPropagation();
    const ok = await copyTextToClipboard(event.url);
    onToast(ok ? 'Copied URL to clipboard' : 'Failed to copy URL');
  };

  return (
    <button type="button" className={`events-timeline-item ${actionClass} ${isSelected ? 'events-timeline-item--selected' : ''}`} onClick={() => onSelect(event.event_id)}>
      <span className="events-corner-id">#{event.event_id}</span>
      <span className={`events-timeline-dot ${actionClass}`} />
      {!isLast && <span className="events-timeline-line" />}
      <div className="events-timeline-content">
        <div className="events-timeline-row">
          <span className="events-timestamp">{formatDateTime(event.timestamp)}</span>
          <span className={`events-action-badge ${actionClass}`}>{event.guard_action.toUpperCase()}</span>
        </div>
        <div className="events-url-row">
          <span className="events-url-text events-url-copy" role="button" tabIndex={0} onClick={handleCopy} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && handleCopy(e)}>
            {event.url}
          </span>
        </div>
      </div>
    </button>
  );
}
