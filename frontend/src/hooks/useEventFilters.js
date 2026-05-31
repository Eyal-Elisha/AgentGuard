import { useMemo, useState } from 'react';

const ACTION_OPTIONS = ['All', 'Block', 'Warn', 'Allow'];

/**
 * Provides client-side filtering (by guard_action) and sorting (by timestamp)
 * for a raw events array. Keeps EventsView.jsx clean.
 */
export function useEventFilters(events) {
  const [filterAction, setFilterAction] = useState('All');
  const [sortOrder, setSortOrder] = useState('desc'); // newest first

  const filteredEvents = useMemo(() => {
    let result = filterAction === 'All'
      ? [...events]
      : events.filter((e) => e.guard_action === filterAction);

    result.sort((a, b) => {
      const diff = new Date(a.timestamp) - new Date(b.timestamp);
      return sortOrder === 'asc' ? diff : -diff;
    });

    return result;
  }, [events, filterAction, sortOrder]);

  function toggleSort() {
    setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
  }

  return {
    filterAction, setFilterAction,
    sortOrder, toggleSort,
    filteredEvents,
    actionOptions: ACTION_OPTIONS,
    totalCount: events.length,
  };
}
