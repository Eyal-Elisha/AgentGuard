import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';

export default function ProtectedRoute() {
  const { currentUser, isLoading } = useAuth();

  if (isLoading) {
    return <div style={{ color: 'white', padding: '2rem', textAlign: 'center' }}>Loading...</div>;
  }

  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
