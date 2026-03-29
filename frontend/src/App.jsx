import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import RulesDashboard from './components/RulesDashboard/RulesDashboard.jsx';
import SessionsDashboard from './components/SessionsDashboard/SessionsDashboard.jsx';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionsDashboard />} />
        <Route path="/rules" element={<RulesDashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
