import { useParams } from 'react-router-dom';
import { useEvents } from '../../hooks/useEvents.js';
import { useEventFilters } from '../../hooks/useEventFilters.js';
import EventsHeader from './EventsHeader.jsx';
import EventFilterBar from './EventFilterBar.jsx';
import EventTimeline from './EventTimeline.jsx';
import EventAnalysis from './EventAnalysis.jsx';
import '../SessionsDashboard/SessionsDashboard.css';
import './EventsView.css';

function EventsView() {
  const { sessionId } = useParams();
  const {
    events, ruleAnalysis, selectedEventId, setSelectedEventId,
    sessionMeta, selectedEvent, isLoading, error, resolvedSessionId,
  } = useEvents(sessionId);

  const {
    filterAction, setFilterAction,
    sortOrder, toggleSort,
    filteredEvents, actionOptions, totalCount,
  } = useEventFilters(events);

  return (
    <div className="sessions-page events-view-root">
      <main className="sessions-dashboard-main events-view-main">
        <section className="sessions-dashboard-card events-view-card">
          <EventsHeader sessionId={resolvedSessionId} meta={sessionMeta} />

          {isLoading && <div className="sessions-loading" role="status">Loading events...</div>}
          {error && <div className="sessions-error-alert" role="alert">{error}</div>}

          {!isLoading && !error && events.length === 0 && (
            <div className="sessions-empty-state">No events recorded for this session.</div>
          )}

          {!isLoading && !error && events.length > 0 && (
            <>
              <EventFilterBar
                filterAction={filterAction}
                onFilterChange={(action) => { setFilterAction(action); setSelectedEventId(null); }}
                sortOrder={sortOrder}
                onToggleSort={toggleSort}
                actionOptions={actionOptions}
                filteredCount={filteredEvents.length}
                totalCount={totalCount}
              />
              <div className="events-view-grid">
                <EventTimeline
                  events={filteredEvents}
                  selectedEventId={selectedEventId}
                  onSelectEvent={setSelectedEventId}
                />
                <EventAnalysis
                  selectedEvent={selectedEvent}
                  ruleAnalysisRows={ruleAnalysis}
                />
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}

export default EventsView;
