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
    const interval = setInterval(fetchIncidents, 5000); // Polling for updates
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Active Incidents</h1>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <IncidentTable incidents={incidents} />
      )}
    </div>
  );
};

export default IncidentsPage;
