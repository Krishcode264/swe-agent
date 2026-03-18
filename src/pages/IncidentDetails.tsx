import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { Incident, TimelineEvent } from '../types/incident';
import TimelineView from '../components/TimelineView';
import StatusBadge from '../components/StatusBadge';
import ReportView from '../components/ReportView';
import { FileText, List, ArrowLeft, GitBranch, Server, User, Globe } from 'lucide-react';

type Tab = 'details' | 'report';

const IncidentDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [tab, setTab] = useState<Tab>('details');
  const [report, setReport] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

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

  const fetchReport = async () => {
    if (!id || report !== null) return;
    setReportLoading(true);
    setReportError(null);
    try {
      const md = await api.getReport(id);
      setReport(md);
    } catch {
      setReportError('Report data is being generated. It will be available once the agent completes the run.');
    } finally {
      setReportLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [id]);

  useEffect(() => {
    if (tab === 'report') fetchReport();
  }, [tab]);

  if (!incident) return (
    <div className="premium-card p-16 flex flex-col items-center justify-center text-slate-400">
      <div className="w-8 h-8 border-4 border-slate-200 border-t-[#0a192f] rounded-full animate-spin mb-4"></div>
      <p className="text-sm font-semibold tracking-wide uppercase">Loading details</p>
    </div>
  );

  const tabBase = 'flex items-center gap-2 py-3.5 px-2 text-sm font-bold border-b-2 transition-all duration-200 ease-in-out';
  const tabActive = 'border-[#0a192f] text-[#0a192f]';
  const tabInactive = 'border-transparent text-slate-400 hover:text-slate-800 hover:border-slate-300';

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header Profile */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
        <div>
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs font-bold tracking-wide text-slate-400 hover:text-[#0a192f] transition-colors duration-200 mb-4 uppercase"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to incidents
          </Link>
          <h1 className="text-3xl font-extrabold text-[#0a192f] flex flex-col sm:flex-row sm:items-center gap-3">
            <span className="font-mono text-slate-400 bg-slate-100 px-3 py-1 rounded-md text-xl border border-slate-200 shadow-sm">{incident.incidentId}</span>
            <span className="hidden sm:inline text-slate-300">—</span>
            <span className="tracking-tight">{incident.title}</span>
          </h1>
        </div>
        <div className="shrink-0 pt-1">
          <StatusBadge status={incident.status} />
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-slate-200/80">
        <nav className="-mb-px flex gap-8">
          <button onClick={() => setTab('details')} className={`${tabBase} ${tab === 'details' ? tabActive : tabInactive}`}>
            <List className="h-4 w-4" />
            Diagnostic Details
          </button>
          <button onClick={() => setTab('report')} className={`${tabBase} ${tab === 'report' ? tabActive : tabInactive}`}>
            <FileText className="h-4 w-4" />
            Resolution Report
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="transition-all duration-300">
        {tab === 'details' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-8">
              {/* Description Card */}
              <div className="premium-card p-8">
                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                  Issue Description
                </h2>
                <div className="bg-slate-50 border border-slate-200/60 p-5 rounded-xl text-sm text-slate-700 whitespace-pre-wrap font-mono leading-relaxed shadow-inner">
                  {incident.description}
                </div>
              </div>

              {/* Meta Grid Card */}
              <div className="premium-card p-0 overflow-hidden">
                 <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-slate-100 bg-slate-50/50">
                    <div className="p-6">
                      <div className="flex items-center gap-2 mb-2">
                        <Globe className="w-4 h-4 text-slate-400" />
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Environment</p>
                      </div>
                      <p className="text-sm font-semibold text-[#0a192f]">{incident.environment}</p>
                    </div>
                    <div className="p-6">
                      <div className="flex items-center gap-2 mb-2">
                        <Server className="w-4 h-4 text-slate-400" />
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Service</p>
                      </div>
                      <p className="text-sm font-semibold text-[#0a192f]">{incident.service}</p>
                    </div>
                    <div className="p-6 border-t border-slate-100">
                      <div className="flex items-center gap-2 mb-2">
                        <GitBranch className="w-4 h-4 text-slate-400" />
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Repository</p>
                      </div>
                      <a href={incident.repository} className="text-sm font-semibold text-[#1e3a5f] hover:text-[#0a192f] hover:underline underline-offset-4 transition-all">
                        {incident.repository.split('/').pop() || incident.repository}
                      </a>
                    </div>
                    <div className="p-6 border-t border-slate-100">
                      <div className="flex items-center gap-2 mb-2">
                        <User className="w-4 h-4 text-slate-400" />
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Reported By</p>
                      </div>
                      <p className="text-sm font-semibold text-[#0a192f]">{incident.reported_by}</p>
                    </div>
                 </div>
              </div>
            </div>

            <div className="lg:col-span-1">
              <div className="premium-card p-8 sticky top-24">
                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-8">Event Timeline</h2>
                <TimelineView events={timeline} />
              </div>
            </div>
          </div>
        )}

        {tab === 'report' && (
          <div className="premium-card overflow-hidden">
            {reportLoading && (
              <div className="p-20 flex flex-col items-center justify-center text-slate-400">
                <div className="w-8 h-8 border-4 border-slate-200 border-t-[#0a192f] rounded-full animate-spin mb-4"></div>
                <p className="text-sm font-semibold tracking-wide uppercase">Validating Report Data</p>
              </div>
            )}
            {reportError && !reportLoading && (
              <div className="p-16 flex flex-col items-center justify-center text-center">
                <div className="bg-slate-50 p-4 rounded-full mb-4">
                  <FileText className="w-8 h-8 text-slate-400" />
                </div>
                <h3 className="text-lg font-bold text-[#0a192f] mb-2">Report Not Ready</h3>
                <p className="text-sm text-slate-500 max-w-md">{reportError}</p>
              </div>
            )}
            {report && !reportLoading && (
              <div className="px-10 py-10 max-w-4xl mx-auto">
                <ReportView markdown={report} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default IncidentDetails;
