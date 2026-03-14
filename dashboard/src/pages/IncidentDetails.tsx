import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { Incident, TimelineEvent } from '../types/incident';
import TimelineView from '../components/TimelineView';
import StatusBadge from '../components/StatusBadge';

const IncidentDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);

  const fetchData = async () => {
    if (!id) return;
    try {
      const [incData, timeData] = await Promise.all([
        api.getIncidentById(id),
        api.getTimeline(id)
      ]);
      setIncident(incData);
      setTimeline(timeData);
    } catch (error) {
      console.error('Failed to fetch details', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [id]);

  if (!incident) return <div className="p-8 text-center text-gray-500">Loading details...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <Link to="/" className="text-sm font-medium text-gray-500 hover:text-gray-700">← Back</Link>
          {incident.incidentId} - {incident.title}
        </h1>
        <StatusBadge status={incident.status} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Description</h2>
            <div className="bg-gray-50 p-4 rounded-md text-sm text-gray-700 whitespace-pre-wrap font-mono">
              {incident.description}
            </div>
            
            <div className="mt-6 grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-500">Environment</p>
                <p className="mt-1 text-sm text-gray-900">{incident.environment}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Service</p>
                <p className="mt-1 text-sm text-gray-900">{incident.service}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Repository</p>
                <a href={incident.repository} className="mt-1 text-sm text-indigo-600 hover:underline">
                  {incident.repository}
                </a>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Reported By</p>
                <p className="mt-1 text-sm text-gray-900">{incident.reported_by}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="col-span-1">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-6">Resolution Timeline</h2>
            <TimelineView events={timeline} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default IncidentDetails;
