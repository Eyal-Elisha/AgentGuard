import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { useAdminUsers } from '../../hooks/useAdminUsers.js';
import { useAdminStats } from '../../hooks/useAdminStats.js';
import AdminStatsBar from './AdminStatsBar.jsx';
import AdminUsersTable from './AdminUsersTable.jsx';
import './AdminDashboard.css';

export default function AdminDashboard() {
  const { currentUser } = useAuth();
  const { users, isLoading: usersLoading, error: usersError } = useAdminUsers();
  const { stats, isLoading: statsLoading, error: statsError } = useAdminStats();

  if (!currentUser?.isAdmin) {
    return <Navigate to="/" replace />;
  }

  const isLoading = usersLoading || statsLoading;
  const error = usersError || statsError;

  return (
    <div className="admin-dashboard-page">
      <div className="admin-header">
        <h1 className="admin-title">Admin Dashboard</h1>
        <p className="admin-subtitle">Global system overview and user management.</p>
      </div>

      {error && <div className="sessions-error-alert">{error}</div>}
      
      {isLoading ? (
        <div className="sessions-loading">Loading admin data...</div>
      ) : (
        <>
          <AdminStatsBar stats={stats} />
          <h2 className="admin-section-title">Registered Users</h2>
          <AdminUsersTable users={users} />
        </>
      )}
    </div>
  );
}
