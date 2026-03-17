import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import IncidentsPage from './pages/IncidentsPage';
import IncidentDetails from './pages/IncidentDetails';
import { Activity } from 'lucide-react';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <Link to="/" className="flex items-center space-x-2 text-indigo-600">
              <Activity className="h-6 w-6" />
              <span className="font-bold text-xl tracking-tight text-gray-900">AgenticFix Platform</span>
            </Link>
          </div>
        </header>

        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          <Routes>
            <Route path="/" element={<IncidentsPage />} />
            <Route path="/incidents/:id" element={<IncidentDetails />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
