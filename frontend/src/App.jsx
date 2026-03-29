import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AgentProvider } from './context/AgentContext.jsx';
import { ProxyProvider } from './context/ProxyContext.jsx';
import AppLayout from './components/Layout/AppLayout.jsx';
import Home from './components/Home/Home.jsx';
import RulesDashboard from './components/RulesDashboard/RulesDashboard.jsx';
import SessionsDashboard from './components/SessionsDashboard/SessionsDashboard.jsx';

function App() {
  return (
    <ProxyProvider>
      <AgentProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<Home />} />
              <Route path="sessions" element={<SessionsDashboard />} />
              <Route path="rules" element={<RulesDashboard />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AgentProvider>
    </ProxyProvider>
  );
}

export default App;
