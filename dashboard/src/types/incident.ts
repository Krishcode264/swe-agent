export interface Incident {
  incidentId: string;
  title: string;
  severity: string;
  service: string;
  reported_by: string;
  environment: string;
  timestamp: string;
  repository: string;
  description: string;
  status: 'queued' | 'running' | 'fix_generated' | 'tests_passed' | 'pr_created' | 'completed' | 'failed';
}

export interface TimelineEvent {
  incidentId: string;
  timestamp: string;
  message: string;
  status: string;
}
