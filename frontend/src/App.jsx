import { Navigate, Route, Routes } from 'react-router-dom';
import EventsView from './components/EventsView/EventsView.jsx';
import SessionsDashboard from './components/SessionsDashboard/SessionsDashboard.jsx';

function App() {
  return (
    <Routes>
      <Route path="/" element={<SessionsDashboard />} />
      <Route path="/sessions/:sessionId/events" element={<EventsView />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;

