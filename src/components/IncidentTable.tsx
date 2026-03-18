import React from 'react';
import { Link } from 'react-router-dom';
import { Incident } from '../types/incident';
import StatusBadge from './StatusBadge';

interface IncidentTableProps {
  incidents: Incident[];
}

const IncidentTable: React.FC<IncidentTableProps> = ({ incidents }) => {
  return (
    <div className="premium-card overflow-hidden">
      <table className="min-w-full divide-y divide-slate-200">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="px-4 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-widest">ID</th>
            <th className="px-4 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-widest">Title</th>
            <th className="px-4 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-widest">Service</th>
            <th className="px-4 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-widest">Status</th>
            <th className="px-4 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-widest hidden sm:table-cell">Time</th>
            <th className="relative px-4 py-4">
              <span className="sr-only">View</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {incidents.map((incident) => (
            <tr
              key={incident.incidentId}
              className="hover:bg-slate-50/80 transition-all duration-200 group"
            >
              <td className="whitespace-nowrap px-4 py-4 text-sm font-semibold text-[#0a192f] font-mono">{incident.incidentId}</td>
              <td className="px-4 py-4 text-sm text-slate-700 font-medium max-w-[200px] truncate">{incident.title}</td>
              <td className="whitespace-nowrap px-4 py-4 text-sm">
                <span className="bg-slate-100/80 text-slate-600 text-xs px-2.5 py-1 rounded-md border border-slate-200 font-semibold tracking-wide">
                  {incident.service}
                </span>
              </td>
              <td className="whitespace-nowrap px-4 py-4 text-sm">
                <StatusBadge status={incident.status} />
              </td>
              <td className="whitespace-nowrap px-4 py-4 text-sm text-slate-500 font-medium hidden sm:table-cell">
                {new Date(incident.timestamp).toLocaleTimeString()}
              </td>
              <td className="whitespace-nowrap px-4 py-4 text-right text-sm font-medium">
                <Link
                  to={`/incidents/${incident.incidentId}`}
                  className="bg-white text-[#0a192f] border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-bold shadow-sm hover:shadow-md hover:bg-slate-50 hover:border-slate-300 transition-all duration-200"
                >
                  View <span aria-hidden="true">&rarr;</span>
                </Link>
              </td>
            </tr>
          ))}
          {incidents.length === 0 && (
            <tr>
              <td colSpan={6} className="px-6 py-16 text-center text-slate-400 text-sm font-medium">
                No incidents found. Awaiting data from the system.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default IncidentTable;
