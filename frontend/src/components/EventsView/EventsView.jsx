import { useParams } from 'react-router-dom';
import { useEvents } from '../../hooks/useEvents.js';
import EventsHeader from './EventsHeader.jsx';
import EventTimeline from './EventTimeline.jsx';
import EventAnalysis from './EventAnalysis.jsx';
import '../SessionsDashboard/SessionsDashboard.css';
import './EventsView.css';

function EventsView() {
  const { sessionId } = useParams();
  const {
    events,
    ruleAnalysis,
    selectedEventId,
    setSelectedEventId,
    sessionMeta,
    selectedEvent,
    isLoading,
    error,
    resolvedSessionId
  } = useEvents(sessionId);

  return (
    <div className="sessions-page events-view-root">
      <main className="sessions-dashboard-main events-view-main">
        <section className="sessions-dashboard-card events-view-card">
          <EventsHeader sessionId={resolvedSessionId} meta={sessionMeta} />

          {isLoading && (
            <div className="sessions-loading" role="status" aria-live="polite">
              Loading events...
            </div>
          )}

          {error && (
            <div className="sessions-error-alert" role="alert">
              {error}
            </div>
          )}

          {!isLoading && !error && events.length === 0 && (
            <div className="sessions-empty-state">
              No events recorded for this session.
            </div>
          )}

          {!isLoading && !error && events.length > 0 && (
            <div className="events-view-grid">
              <EventTimeline
                events={events}
                selectedEventId={selectedEventId}
                onSelectEvent={setSelectedEventId}
              />
              <EventAnalysis
                selectedEvent={selectedEvent}
                ruleAnalysisRows={ruleAnalysis}
              />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default EventsView;
