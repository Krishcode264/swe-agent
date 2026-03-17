// import React, { useEffect, useState } from 'react';
// import { api } from '../services/api';
// import { Incident } from '../types/incident';
// import IncidentTable from '../components/IncidentTable';

// const IncidentsPage: React.FC = () => {
//   const [incidents, setIncidents] = useState<Incident[]>([]);
//   const [loading, setLoading] = useState(true);

//   const fetchIncidents = async () => {
//     try {
//       const data = await api.getIncidents();
//       setIncidents(data);
//     } catch (error) {
//       console.error('Failed to fetch incidents', error);
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     fetchIncidents();
//     const interval = setInterval(fetchIncidents, 5000); // Polling for updates
//     return () => clearInterval(interval);
//   }, []);

//   return (
//     <div>
//       <h1 className="text-2xl font-bold text-gray-900 mb-6">Active Incidents</h1>
//       {loading ? (
//         <p>Loading...</p>
//       ) : (
//         <IncidentTable incidents={incidents} />
//       )}
//     </div>
//   );
// };

// export default IncidentsPage;



import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Incident } from '../types/incident';
import IncidentTable from '../components/IncidentTable';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';

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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 tracking-tight">Active Incidents</h1>
          <p className="text-slate-600 mt-2">Monitor and manage system incidents in real-time</p>
        </div>

        <Card className="border-0 shadow-lg">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="text-center">
                <Spinner className="mx-auto mb-4" />
                <p className="text-slate-600">Loading incidents...</p>
              </div>
            </div>
          ) : incidents.length > 0 ? (
            <IncidentTable incidents={incidents} />
          ) : (
            <div className="py-16 text-center">
              <p className="text-slate-500">No incidents detected</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default IncidentsPage;