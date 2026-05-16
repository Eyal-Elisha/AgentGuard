import { Navigate, Route, Routes } from 'react-router-dom';
import EventsView from './components/EventsView/EventsView.jsx';
import AppLayout from './components/Layout/AppLayout.jsx';
import Home from './components/Home/Home.jsx';
import RulesDashboard from './components/RulesDashboard/RulesDashboard.jsx';
import SessionsDashboard from './components/SessionsDashboard/SessionsDashboard.jsx';
import LoginPage from './components/Auth/LoginPage.jsx';
import SignupPage from './components/Auth/SignupPage.jsx';
import ProtectedRoute from './components/Auth/ProtectedRoute.jsx';
import AdminDashboard from './components/AdminDashboard/AdminDashboard.jsx';
import { AgentProvider } from './context/AgentContext.jsx';
import { ProxyProvider } from './context/ProxyContext.jsx';
import { AuthProvider } from './context/AuthContext.jsx';

function App() {
  return (
    <AuthProvider>
      <ProxyProvider>
        <AgentProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route index element={<Home />} />
                <Route path="sessions" element={<SessionsDashboard />} />
                <Route path="sessions/:sessionId/events" element={<EventsView />} />
                <Route path="rules" element={<RulesDashboard />} />
                <Route path="admin" element={<AdminDashboard />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </AgentProvider>
      </ProxyProvider>
    </AuthProvider>
  );
}

export default App;
