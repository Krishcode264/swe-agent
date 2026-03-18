import React from 'react';

const STATUS_COLORS: Record<string, string> = {
  queued: 'bg-gray-100 text-gray-800',
  running: 'bg-blue-100 text-blue-800',
  fix_generated: 'bg-indigo-100 text-indigo-800',
  tests_passed: 'bg-green-100 text-green-800',
  pr_created: 'bg-purple-100 text-purple-800',
  completed: 'bg-teal-100 text-teal-800',
  failed: 'bg-red-100 text-red-800'
};

interface StatusBadgeProps {
  status: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const colorClass = STATUS_COLORS[status] || 'bg-gray-100 text-gray-800';
  const label = status.replace('_', ' ').toUpperCase();
  
  return (
    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${colorClass}`}>
      {label}
    </span>
  );
};

export default StatusBadge;
