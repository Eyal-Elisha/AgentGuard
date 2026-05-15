import { useEffect, useState } from 'react';
import EventTimelineItem from './EventTimelineItem.jsx';

export default function EventTimeline({ events, selectedEventId, onSelectEvent }) {
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
        {events.map((event, i) => (
          <EventTimelineItem
            key={event.event_id}
            event={event}
            isSelected={event.event_id === selectedEventId}
            isLast={i === events.length - 1}
            onSelect={onSelectEvent}
            onToast={setToast}
          />
        ))}
      </div>
      {toast && <div className="events-toast" role="status">{toast}</div>}
    </section>
  );
}
