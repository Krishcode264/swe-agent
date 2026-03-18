import React from 'react';
import { Link } from 'react-router-dom';
import { Incident } from '../types/incident';
import StatusBadge from './StatusBadge';

interface IncidentTableProps {
  incidents: Incident[];
}

const IncidentTable: React.FC<IncidentTableProps> = ({ incidents }) => {
  return (
    <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
      <table className="min-w-full divide-y divide-gray-300">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">ID</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Title</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Service</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
            <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Time</th>
            <th className="relative px-6 py-3">
              <span className="sr-only">View</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {incidents.map((incident) => (
            <tr key={incident.incidentId}>
              <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">{incident.incidentId}</td>
              <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">{incident.title}</td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{incident.service}</td>
              <td className="whitespace-nowrap px-6 py-4 text-sm">
                <StatusBadge status={incident.status} />
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                {new Date(incident.timestamp).toLocaleTimeString()}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                <Link to={`/incidents/${incident.incidentId}`} className="text-indigo-600 hover:text-indigo-900">
                  Select
                </Link>
              </td>
            </tr>
          ))}
          {incidents.length === 0 && (
            <tr>
              <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                No incidents found. Trigger one from the dummy frontend!
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default IncidentTable;
