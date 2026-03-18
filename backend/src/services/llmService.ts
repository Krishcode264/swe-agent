import { logger } from '../utils/logger';

export interface ParsedJiraIncident {
  incidentId: string;
  title: string;
  severity: string;
  service: string;
  reported_by: string;
  environment: string;
  description: string;
  steps_to_reproduce: string[];
  error_log: string;
  expected_behavior: string;
  actual_behavior: string;
  repository: string;
}

export interface ParsedGithubIncident {
  title: string;
  severity: string;
  service: string;
  environment: string;
  description: string;
  steps_to_reproduce: string[];
  error_log: string;
  expected_behavior: string;
  actual_behavior: string;
  repository: string;
  tags: string[];
}

class LLMService {
  private geminiKey = process.env.GEMINI_API_KEY;
  private ollamaUrl = process.env.OLLAMA_BASE_URL;
  private ollamaModel = process.env.OLLAMA_MODEL || 'qwen2.5-coder:7b';

  async parseGithubIssue(payload: any): Promise<ParsedGithubIncident> {
    const issue = payload.issue || {};
    const repoName = payload.repository?.full_name || 'unknown';
    const prompt = `
      You are an expert system that converts a raw GitHub issue report (written by a human) into a structured software incident record.
      
      ## GitHub Issue
      - **Repository**: ${repoName}
      - **Title**: ${issue.title || ''}
      - **Body**:
      \`\`\`
      ${issue.body || 'No description provided.'}
      \`\`\`
      
      ## Task
      Parse the above issue and respond ONLY with a valid JSON object matching these exact fields:
      - title: A clean, concise title for the incident.
      - severity: Classify as "P0 - Blocker", "P1 - Critical", "P2 - Major", or "P3 - Minor" based on the language used.
      - service: Identify the affected service from the repository or description (e.g., "node-service", "python-service", "frontend"). Default to "unknown-service".
      - environment: "production", "staging", or "development". Default to "production".
      - description: A clean summary of the problem in 2-3 sentences.
      - steps_to_reproduce: An array of steps to reproduce the issue. Extract if present, otherwise return [].
      - error_log: Extract any stack traces, error messages, or log snippets verbatim from the body. Default to empty string "".
      - expected_behavior: What the user expected to happen.
      - actual_behavior: What actually happened.
      - repository: The GitHub repository in "owner/repo" format. Use "${repoName}".
      - tags: An array of relevant tags (e.g., ["bug", "crash", "auth", "payments"]).
    `;

    if (this.geminiKey) {
      try {
        return await this.callGemini(prompt) as unknown as ParsedGithubIncident;
      } catch (err) {
        logger.warn('Gemini GitHub parsing failed, trying Ollama...', err);
      }
    }

    if (this.ollamaUrl) {
      try {
        return await this.callOllama(prompt) as unknown as ParsedGithubIncident;
      } catch (err) {
        logger.warn('Ollama GitHub parsing failed, using manual fallback...', err);
      }
    }

    return this.githubManualFallback(payload);
  }

  async parseJiraPayload(payload: any): Promise<ParsedJiraIncident> {
    const prompt = `
      You are an expert system that parses Jira webhook payloads into structured incident data.
      
      ## Jira Payload
      \`\`\`json
      ${JSON.stringify(payload, null, 2)}
      \`\`\`
      
      ## Task
      Extract the following fields from the Jira payload. Respond ONLY with a valid JSON object matching these fields:
      - incidentId: Use the Jira issue key (e.g., "PROJ-123").
      - title: Use the issue summary.
      - severity: Map Jira priority to "P0", "P1", "P2", or "P3".
      - service: Try to identify the affected service (e.g., "node-service", "python-service") from summary/description.
      - reported_by: Display name of the reporter.
      - environment: Mention of "prod", "staging", or "dev". Default "production".
      - description: Full issue description.
      - steps_to_reproduce: Extract list of steps if any.
      - error_log: Extract stack traces/error messages if any.
      - expected_behavior: What was expected.
      - actual_behavior: What actually happened.
      - repository: The GitHub repository URL if mentioned (default "https://github.com/Krishcode264/shopstack-platform.git").
    `;

    // Try Gemini first
    if (this.geminiKey) {
      try {
        return await this.callGemini(prompt);
      } catch (err) {
        logger.warn('Gemini parsing failed, trying Ollama...', err);
      }
    }

    // Try Ollama second
    if (this.ollamaUrl) {
      try {
        return await this.callOllama(prompt);
      } catch (err) {
        logger.warn('Ollama parsing failed, using manual fallback...', err);
      }
    }

    // Final fallback
    return this.manualFallback(payload);
  }

  private async callGemini(prompt: string): Promise<ParsedJiraIncident> {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${this.geminiKey}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { response_mime_type: 'application/json' }
      })
    });

    const data = await response.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) throw new Error('Empty response from Gemini');
    return JSON.parse(text);
  }

  private async callOllama(prompt: string): Promise<ParsedJiraIncident> {
    const response = await fetch(`${this.ollamaUrl}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: this.ollamaModel,
        prompt: prompt,
        stream: false,
        format: 'json'
      })
    });

    const data = await response.json();
    if (!data.response) throw new Error('Empty response from Ollama');
    return JSON.parse(data.response);
  }

  private manualFallback(payload: any): ParsedJiraIncident {
    const issue = payload.issue || {};
    const fields = issue.fields || {};
    
    return {
      incidentId: issue.key || `JIRA-${Date.now()}`,
      title: fields.summary || 'Untitiled Jira Issue',
      severity: fields.priority?.name === 'Highest' ? 'P0' : 'P1',
      service: 'unknown',
      reported_by: fields.reporter?.displayName || 'Jira Webhook',
      environment: 'production',
      description: fields.description || '',
      steps_to_reproduce: [],
      error_log: '',
      expected_behavior: '',
      actual_behavior: '',
      repository: 'https://github.com/Krishcode264/shopstack-platform.git'
    };
  }
  private githubManualFallback(payload: any): ParsedGithubIncident {
    const issue = payload.issue || {};
    return {
      title: issue.title || 'Unknown GitHub Issue',
      severity: 'P1 - Critical',
      service: 'unknown-service',
      environment: 'production',
      description: issue.body || '',
      steps_to_reproduce: [],
      error_log: '',
      expected_behavior: '',
      actual_behavior: '',
      repository: payload.repository?.full_name || 'unknown',
      tags: issue.labels?.map((l: any) => l.name) || []
    };
  }
}

export const llmService = new LLMService();
