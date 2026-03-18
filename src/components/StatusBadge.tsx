import React from 'react';

const STATUS_STYLES: Record<string, string> = {
  queued:        'bg-white text-slate-600 border border-slate-200 shadow-sm',
  running:       'bg-[#0a192f] text-white border border-[#0a192f] shadow-sm shadow-[#0a192f]/20',
  fix_generated: 'bg-[#1e3a5f] text-white border border-[#1e3a5f] shadow-sm',
  tests_passed:  'bg-white text-[#0a192f] border border-[#0a192f]/20 shadow-sm',
  pr_created:    'bg-slate-100 text-[#0a192f] border border-slate-300 shadow-sm',
  completed:     'bg-white text-[#0a192f] border border-slate-300 shadow-sm',
  failed:        'bg-black text-white border border-black shadow-sm',
  reporting:     'bg-slate-800 text-white border border-slate-800 shadow-sm',
};

interface StatusBadgeProps {
  status: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const styleClass = STATUS_STYLES[status] || 'bg-white text-slate-600 border border-slate-200 shadow-sm';
  const label = status.replace(/_/g, ' ').toUpperCase();

  return (
    <span className={`px-2.5 py-1 inline-flex text-xs font-bold tracking-wide rounded-md ${styleClass}`}>
      {label}
    </span>
  );
};

export default StatusBadge;
