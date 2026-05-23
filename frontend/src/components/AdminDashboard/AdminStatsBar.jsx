export default function AdminStatsBar({ stats }) {
  if (!stats) return null;

  return (
    <div className="admin-stats-grid">
      <div className="admin-stat-card">
        <span className="admin-stat-label">Total Users</span>
        <span className="admin-stat-value">{stats.total_users}</span>
      </div>
      <div className="admin-stat-card">
        <span className="admin-stat-label">Total Sessions</span>
        <span className="admin-stat-value">{stats.total_sessions}</span>
      </div>
      <div className="admin-stat-card">
        <span className="admin-stat-label">Total Events</span>
        <span className="admin-stat-value">{stats.total_events}</span>
      </div>
    </div>
  );
}
