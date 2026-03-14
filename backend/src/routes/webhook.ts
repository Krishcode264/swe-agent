import { Router, Request, Response } from 'express';
import { githubService } from '../services/githubService';
import { incidentService } from '../services/incidentService';
import { queueService } from '../services/queueService';
import { logger } from '../utils/logger';

const router = Router();

router.post('/github', async (req: Request, res: Response) => {
  try {
    const payload = req.body;
    
    // Webhook validation can be added here
    logger.info('Received webhook payload');

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
