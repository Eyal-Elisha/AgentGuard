const ACTION_CLASS_MAP = {
  Block: 'event-action--block',
  Warn: 'event-action--warn',
  Allow: 'event-action--allow',
};

export default function EventTimeline({
  events,
  selectedEventId,
  onSelectEvent,
}) {
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
              <span className={`events-timeline-dot ${actionClass}`} />
              {index < events.length - 1 && <span className="events-timeline-line" />}
              <div className="events-timeline-content">
                <div className="events-timeline-row">
                  <span className="events-timestamp">{event.timestamp}</span>
                  <span className={`events-action-badge ${actionClass}`}>
                    {event.guard_action.toUpperCase()}
                  </span>
                </div>
                <p className="events-url">URL: {event.url}</p>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
