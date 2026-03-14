import { logger } from '../utils/logger';
import { IIncident } from '../models/Incident';

export const githubService = {
  extractIncidentData: (payload: any): Partial<IIncident> => {
    // Basic extraction from a simulated or real github webhook payload
    const title = payload.issue?.title || payload.title || 'Unknown Issue';
    const body = payload.issue?.body || payload.body || '';
    const repository = payload.repository?.html_url || payload.repository || 'unknown-repo';
    
    // Fallback extraction
    const generateId = () => `INC-${Math.floor(Math.random() * 10000).toString().padStart(4, '0')}`;
    
    return {
      incidentId: payload.id ? `INC-${payload.id}` : generateId(),
      title,
      description: body,
      repository,
      severity: 'P1 - Critical',
      service: 'unknown-service',
      reported_by: payload.sender?.login || 'system',
      environment: 'staging',
      status: 'queued'
    };
  }
};
