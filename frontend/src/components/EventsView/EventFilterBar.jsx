import './EventFilterBar.css';

const ACTION_COLOR = {
  All: 'all',
  Block: 'block',
  Warn: 'warn',
  Allow: 'allow',
};

export default function EventFilterBar({
  filterAction, onFilterChange,
  sortOrder, onToggleSort,
  actionOptions, filteredCount, totalCount,
}) {
  return (
    <div className="event-filter-bar">
      <div className="event-filter-pills">
        {actionOptions.map((action) => (
          <button
            key={action}
            type="button"
            className={`event-filter-pill event-filter-pill--${ACTION_COLOR[action]} ${filterAction === action ? 'event-filter-pill--active' : ''}`}
            onClick={() => onFilterChange(action)}
            aria-pressed={filterAction === action}
          >
            {action}
          </button>
        ))}
      </div>

      <div className="event-filter-right">
        <span className="event-filter-count">
          {filteredCount < totalCount
            ? `${filteredCount} of ${totalCount} events`
            : `${totalCount} event${totalCount !== 1 ? 's' : ''}`}
        </span>
        <button
          type="button"
          className="event-sort-btn"
          onClick={onToggleSort}
          title={sortOrder === 'desc' ? 'Currently: Newest First' : 'Currently: Oldest First'}
        >
          {sortOrder === 'desc' ? '↓ Newest First' : '↑ Oldest First'}
        </button>
      </div>
    </div>
  );
}
