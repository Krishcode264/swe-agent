import { Router, Request, Response } from 'express';
import { githubService } from '../services/githubService';
import { incidentService } from '../services/incidentService';
import { queueService } from '../services/queueService';
import { logger } from '../utils/logger';

const router = Router();

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
