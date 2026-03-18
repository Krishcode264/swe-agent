import { logger } from '../utils/logger';
import { IIncident } from '../models/Incident';
import crypto from 'crypto';

export const githubService = {
  /**
   * Extracts non-content metadata from a GitHub webhook payload.
   * Content fields (title, description, error_log, service, etc.) are
   * parsed by the LLM via llmService.parseGithubIssue() instead.
   */
  extractMetadata: (payload: any): Partial<IIncident> => {
    return {
      incidentId: payload.issue?.id ? `INC-GH-${payload.issue.id}` : `INC-GH-${crypto.randomUUID()}`,
      source: 'github_issue',
      issue_number: payload.issue?.number,
      issue_url: payload.issue?.html_url,
      triggered_by: payload.issue?.user?.login || payload.sender?.login || 'github',
      assigned_agent: 'swe-agent',
      status: 'queued',
    };
  }
};
