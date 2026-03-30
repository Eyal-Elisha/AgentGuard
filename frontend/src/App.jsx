import { Navigate, Route, Routes } from 'react-router-dom';
import EventsView from './components/EventsView/EventsView.jsx';
import AppLayout from './components/Layout/AppLayout.jsx';
import Home from './components/Home/Home.jsx';
import RulesDashboard from './components/RulesDashboard/RulesDashboard.jsx';
import SessionsDashboard from './components/SessionsDashboard/SessionsDashboard.jsx';
import { AgentProvider } from './context/AgentContext.jsx';
import { ProxyProvider } from './context/ProxyContext.jsx';

function App() {
  return (
    <ProxyProvider>
      <AgentProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<Home />} />
            <Route path="sessions" element={<SessionsDashboard />} />
            <Route path="sessions/:sessionId/events" element={<EventsView />} />
            <Route path="rules" element={<RulesDashboard />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AgentProvider>
    </ProxyProvider>
  );
}

export default App;
