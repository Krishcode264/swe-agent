import { Router, Request, Response } from 'express';
import { githubService } from '../services/githubService';
import { incidentService } from '../services/incidentService';
import { queueService } from '../services/queueService';
import { llmService } from '../services/llmService';
import { logger } from '../utils/logger';

const router = Router();

router.post('/simulate', async (req: Request, res: Response): Promise<any> => {
  try {
    const rawBody = req.body;
    logger.info('Simulating incident ingestion', rawBody.incidentId);

    // IMPORTANT: Strip the 'id' field sent by the frontend — Mongoose maps 'id'
    // to the internal _id virtual, which expects a valid ObjectId. Our incident
    // IDs like "INC-006" are NOT valid ObjectIds, so we must remove this field.
    const { id, _id, ...incidentData } = rawBody;

    let incident: any;
    let mongoOk = false;

    // Try to save to MongoDB (non-blocking if Mongo is down)
    try {
      incident = await incidentService.createIncident(incidentData);
      mongoOk = true;
    } catch (dbErr: any) {
      logger.error('MongoDB save failed, falling back to Redis-only mode', dbErr.message);
      // Build a plain incident object so we can still push to Redis
      incident = {
        ...incidentData,
        status: 'queued',
        createdAt: new Date().toISOString(),
      };
    }

    // Always push to Redis queue — the agent worker doesn't need MongoDB
    await queueService.pushTask(incident);

    if (!mongoOk) {
      logger.info(`Pushed INC ${incident.incidentId} to queue (Redis-only, MongoDB unavailable)`);
    }

    res.status(202).json({ 
      message: mongoOk 
        ? 'Simulated incident queued successfully' 
        : 'Simulated incident queued (Redis only — MongoDB unavailable)',
      incidentId: incident.incidentId 
    });
  } catch (error) {
    logger.error('Error simulating incident', error);
    res.status(500).json({ error: 'Failed to simulate incident' });
  }
});

router.post('/github', async (req: Request, res: Response): Promise<any> => {
  try {
    const githubEvent = req.headers['x-github-event'];
    if (githubEvent !== 'issues') {
      return res.status(200).send('ignore');
    }

    const payload = req.body;
    
    if (payload.action !== 'labeled' || payload.label?.name !== 'assign to agent') {
      return res.status(200).send('ignore');
    }

    logger.info('Received valid assigned github issue payload');

    // Convert issue to structured incident
    const incidentData = githubService.extractIncidentData(payload);
    
    // Create in DB
    const incident = await incidentService.createIncident(incidentData);
    
    // Push to Redis Queue
    await queueService.pushTask(incident);
    
    res.status(202).json({ message: 'Incident queued successfully', incidentId: incident.incidentId });
  } catch (error) {
    logger.error('Error processing GitHub webhook', error);
    res.status(500).json({ error: 'Failed to process webhook' });
  }
});

router.post('/jira', async (req: Request, res: Response): Promise<any> => {
  try {
    const payload = req.body;
    const issue = payload.issue || {};
    const labels: string[] = issue.fields?.labels || [];
    
    // Check if Jira issue is labeled with "trigger-agent"
    if (!labels.includes('trigger-agent')) {
      logger.info('Jira issue does not have "trigger-agent" label, ignoring', issue.key);
      return res.status(200).send('ignore');
    }

    logger.info('Received valid labeling event from Jira', issue.key);

    // Call LLM to parse payload into structured incident data
    const parsedData = await llmService.parseJiraPayload(payload);
    
    // Enrich with additional metadata
    const incidentData = {
      ...parsedData,
      source: 'jira',
      status: 'queued' as any,
      triggered_by: payload.user?.displayName || 'Jira Webhook',
      timestamp: new Date()
    };

    // Create in DB
    const incident = await incidentService.createIncident(incidentData);
    
    // Push to Redis Queue
    await queueService.pushTask(incident);
    
    res.status(202).json({ 
      message: 'Jira incident parsed and queued successfully', 
      incidentId: incident.incidentId 
    });
  } catch (error) {
    logger.error('Error processing Jira webhook', error);
    res.status(500).json({ error: 'Failed to process Jira webhook' });
  }
});

export default router;
