import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import IncidentsPage from './pages/IncidentsPage';
import IncidentDetails from './pages/IncidentDetails';
import { Activity } from 'lucide-react';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-8 h-8 rounded-xl bg-[#0a192f] flex items-center justify-center shadow-sm shadow-[#0a192f]/20 group-hover:shadow-md transition-all duration-300">
                <Activity className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-lg tracking-tight text-[#0a192f]">AgenticFix</span>
              <span className="text-slate-400 text-sm font-medium hidden sm:block">/ Platform</span>
            </Link>
            <div className="flex items-center gap-2 bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-full shadow-sm">
              <span className="w-2 h-2 rounded-full bg-[#0a192f] animate-pulse inline-block"></span>
              <span className="text-xs font-semibold text-[#0a192f]">System Live</span>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
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
