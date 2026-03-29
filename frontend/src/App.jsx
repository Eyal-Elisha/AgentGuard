import { useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import EventsView from './components/EventsView/EventsView.jsx';
import SessionsDashboard from './components/SessionsDashboard/SessionsDashboard.jsx';

function App() {
  const [selectedAgent, setSelectedAgent] = useState('Gemini');
  const [isProxyActive, setIsProxyActive] = useState(false);

  const handleAgentSelect = (agent) => {
    if (agent !== selectedAgent) {
      setIsProxyActive(false);
    }
    setSelectedAgent(agent);
  };

  const handleProxyToggle = () => {
    setIsProxyActive((prev) => !prev);
  };

  return (
    <Routes>
      <Route path="/" element={
        <SessionsDashboard 
          selectedAgent={selectedAgent}
          onAgentSelect={handleAgentSelect}
          isProxyActive={isProxyActive}
          onProxyToggle={handleProxyToggle}
        />
      } />
      <Route path="/sessions/:sessionId/events" element={
        <EventsView 
          selectedAgent={selectedAgent}
          onAgentSelect={handleAgentSelect}
          isProxyActive={isProxyActive}
          onProxyToggle={handleProxyToggle}
        />
      } />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;

