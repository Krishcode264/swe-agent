import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Incident } from '../types/incident';
import IncidentTable from '../components/IncidentTable';

const IncidentsPage: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchIncidents = async () => {
    try {
      const data = await api.getIncidents();
      setIncidents(data);
    } catch (error) {
      console.error('Failed to fetch incidents', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-[#0a192f]">
          Active Incidents
        </h1>
        <p className="text-slate-500 text-sm mt-2 font-medium">Monitor and manage autonomous resolution pipelines in real-time.</p>
      </div>
      
      {loading ? (
        <div className="premium-card p-16 flex flex-col items-center justify-center text-slate-400">
          <div className="w-8 h-8 border-4 border-slate-200 border-t-[#0a192f] rounded-full animate-spin mb-4"></div>
          <p className="text-sm font-semibold tracking-wide uppercase">Establishing connection</p>
        </div>
      ) : (
        <div className="premium-shadow rounded-2xl bg-white border border-slate-200/60 overflow-hidden">
          <IncidentTable incidents={incidents} />
        </div>
      )}
    </div>
  );
};

export default IncidentsPage;
