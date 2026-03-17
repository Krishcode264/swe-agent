// 

import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { Incident, TimelineEvent } from '../types/incident';
import TimelineView from '../components/TimelineView';
import StatusBadge from '../components/StatusBadge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { Spinner } from '@/components/ui/spinner';

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

  if (!incident) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-center">
          <Spinner className="mx-auto mb-4" />
          <p className="text-slate-600">Loading incident details...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link to="/">
            <Button variant="ghost" className="mb-4">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-4xl font-bold text-slate-900 tracking-tight">
                {incident.incidentId}
              </h1>
              <p className="text-xl text-slate-600 mt-2">{incident.title}</p>
            </div>
            <StatusBadge status={incident.status} />
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Description Card */}
          <div className="lg:col-span-2">
            <Card className="border-0 shadow-lg h-full">
              <CardHeader>
                <CardTitle>Description</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="bg-slate-900 text-slate-50 p-4 rounded-lg font-mono text-sm overflow-x-auto whitespace-pre-wrap break-words">
                  {incident.description}
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-6 pt-4 border-t border-slate-200">
                  <div>
                    <p className="text-sm font-semibold text-slate-600 uppercase tracking-wide">
                      Environment
                    </p>
                    <p className="mt-2 text-base font-medium text-slate-900">
                      {incident.environment}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-600 uppercase tracking-wide">
                      Service
                    </p>
                    <p className="mt-2 text-base font-medium text-slate-900">
                      {incident.service}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-600 uppercase tracking-wide">
                      Repository
                    </p>
                    <a
                      href={incident.repository}
                      className="mt-2 text-base font-medium text-blue-600 hover:text-blue-700 hover:underline break-all"
                    >
                      {incident.repository}
                    </a>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-600 uppercase tracking-wide">
                      Reported By
                    </p>
                    <p className="mt-2 text-base font-medium text-slate-900">
                      {incident.reported_by}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Timeline Card */}
          <div className="lg:col-span-1">
            <Card className="border-0 shadow-lg h-full sticky top-8">
              <CardHeader>
                <CardTitle className="text-lg">Resolution Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <TimelineView events={timeline} />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IncidentDetails;