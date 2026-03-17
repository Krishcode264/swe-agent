import { Router, Request, Response } from 'express';
import { githubService } from '../services/githubService';
import { incidentService } from '../services/incidentService';
import { queueService } from '../services/queueService';
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

export default router;
