import { logger } from '../utils/logger';
import { IIncident } from '../models/Incident';
import crypto from 'crypto';

export const githubService = {
  extractIncidentData: (payload: any): Partial<IIncident> => {
    // Generate UUID task ID via crypto
    const generateId = () => crypto.randomUUID();
    
    // extra_info might be used by dummy backend simulator, 
    // but direct triggers might have these at root level.
    const source = payload.extra_info || payload;
    
    return {
      incidentId: source.id || source.incidentId || (payload.id ? `INC-${payload.id}` : generateId()),
      source: payload.extra_info ? 'simulator' : (payload.issue ? 'github_issue' : 'direct_trigger'),
      repository: payload.repository?.full_name || source.repository || 'Rezinix-AI/shopstack-platform',
      issue_number: payload.issue?.number || source.issue_number,
      title: payload.issue?.title || payload.title || source.title || 'Unknown Issue',
      description: payload.issue?.body || payload.body || source.description || '',
      issue_url: payload.issue?.html_url || source.issue_url,
      // Metadata fields
      reported_by: source.reported_by || 'system',
      triggered_by: payload.issue?.user?.login || payload.sender?.login || source.reported_by || 'system',
      assigned_agent: 'swe-agent',
      status: 'queued',
      timestamp: source.timestamp ? new Date(source.timestamp) : new Date(),
      // Core error details
      severity: source.severity || 'P1 - Critical',
      service: source.service || 'unknown-service',
      environment: source.environment || 'staging',
      steps_to_reproduce: source.steps_to_reproduce || [],
      error_log: source.error_log || '',
      expected_behavior: source.expected_behavior || '',
      actual_behavior: source.actual_behavior || '',
      recent_changes: source.recent_changes || '',
      tags: source.tags || []
    };
  }
};
