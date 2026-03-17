import { logger } from '../utils/logger';
import { IIncident } from '../models/Incident';
import crypto from 'crypto';

export const githubService = {
  extractIncidentData: (payload: any): Partial<IIncident> => {
    // Generate UUID task ID via crypto
    const generateId = () => crypto.randomUUID();
    
    return {
      incidentId: payload.id ? `INC-${payload.id}` : generateId(),
      source: 'github_issue',
      repository: payload.repository?.full_name || 'unknown-repo',
      issue_number: payload.issue?.number,
      title: payload.issue?.title || payload.title || 'Unknown Issue',
      description: payload.issue?.body || payload.body || '',
      issue_url: payload.issue?.html_url,
      triggered_by: payload.issue?.user?.login || payload.sender?.login || 'system',
      assigned_agent: 'swe-agent',
      status: 'queued', // This means waiting for agent to pick up
      // keep basic fallback fields
      severity: 'P1 - Critical',
      service: 'unknown-service',
      environment: 'staging'
    };
  }
};
