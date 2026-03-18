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
      You are an expert software engineering incident analyst. You have received a raw Jira webhook payload (in JSON format). Your job is to extract and synthesize a fully structured incident record from it.
      
      ## Raw Jira Webhook Payload
      \`\`\`json
      ${JSON.stringify(payload, null, 2)}
      \`\`\`
      
      ## Instructions
      Carefully read the entire payload above. The issue details are typically found at:
      - payload.issue.fields.summary → the issue title/summary
      - payload.issue.fields.description → may be plain text, Atlassian Document Format (ADF), or a string
      - payload.issue.fields.priority.name → priority level
      - payload.issue.fields.reporter.displayName → reporter name
      - payload.issue.fields.assignee → assignee
      - payload.issue.key → the Jira issue key (e.g., "PROJ-123")
      - payload.issue.fields.comment → comments with extra context
      
      **CRITICAL RULES:**
      1. NEVER return "Untitled Jira Issue" or any generic placeholder as the title. If summary is empty, synthesize a concise, specific technical title from the description content.
      2. The description field in Atlassian Document Format (ADF) stores text inside content[].content[].text — extract ALL text from it.
      3. For error_log: extract any stack traces, exception messages, log snippets verbatim. Leave empty string if none.
      4. For steps_to_reproduce: extract numbered/bulleted steps if present, else return [].
      5. For service: infer from the issue content (e.g., "node-service", "python-service", "frontend"). Default to "unknown-service" only if truly undetectable.
      6. RESPOND ONLY with a single valid JSON object, no markdown, no extra text.

      ## Required JSON Output
      {
        "incidentId": "<Jira issue key, e.g. PROJ-123>",
        "title": "<Clear, specific technical title — NO generic placeholders>",
        "severity": "<P0 - Blocker | P1 - Critical | P2 - Major | P3 - Minor — map from Jira priority>",
        "service": "<affected service, e.g. node-service | python-service | frontend>",
        "reported_by": "<reporter display name>",
        "environment": "<production | staging | development>",
        "description": "<A clear 3-5 sentence technical summary of the problem synthesized from the issue content>",
        "steps_to_reproduce": ["<step 1>", "<step 2>"],
        "error_log": "<verbatim stack trace or error message if present, else empty string>",
        "expected_behavior": "<what should happen>",
        "actual_behavior": "<what actually happens>",
        "repository": "<GitHub repo URL if mentioned, else 'https://github.com/Krishcode264/shopstack-platform.git'>"
      }
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
    
    // Try to extract plain text from ADF description format
    let descriptionText = '';
    if (typeof fields.description === 'string') {
      descriptionText = fields.description;
    } else if (fields.description?.content) {
      // ADF format: recursively extract text nodes
      const extractAdfText = (node: any): string => {
        if (!node) return '';
        if (node.type === 'text') return node.text || '';
        if (node.content) return node.content.map(extractAdfText).join(' ');
        return '';
      };
      descriptionText = extractAdfText(fields.description).trim();
    }

    // Synthesize title from summary or description
    const summary = fields.summary || '';
    const synthesizedTitle = summary || 
      (descriptionText ? descriptionText.split('.')[0].trim().substring(0, 120) : null) ||
      `Jira Issue ${issue.key || 'Unknown'}`;
    
    return {
      incidentId: issue.key || `JIRA-${Date.now()}`,
      title: synthesizedTitle,
      severity: fields.priority?.name === 'Highest' || fields.priority?.name === 'Blocker' ? 'P0 - Blocker' : 'P1 - Critical',
      service: 'unknown-service',
      reported_by: fields.reporter?.displayName || fields.creator?.displayName || 'Jira Webhook',
      environment: 'production',
      description: descriptionText || summary || 'No description provided.',
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
