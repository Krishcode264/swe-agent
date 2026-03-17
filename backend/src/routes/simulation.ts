import { Router, Request, Response } from 'express';
import { githubService } from '../services/githubService';
import { incidentService } from '../services/incidentService';
import { queueService } from '../services/queueService';
import { logger } from '../utils/logger';

const router = Router();

/**
 * Endpoint for manual/direct incident simulation.
 * This skips GitHub's specific webhook signatures but follows the same pipeline.
 */
router.post('/trigger', async (req: Request, res: Response) => {
  try {
    const payload = req.body;
    logger.info(`Received direct simulation trigger: ${payload.title || payload.id}`);

    // Standardize data using the same service (it now handles root-level objects)
    const incidentData = githubService.extractIncidentData(payload);
    
    // Create in DB
    const incident = await incidentService.createIncident(incidentData);
    
    // Push to Redis Queue
    await queueService.pushTask(incident);
    
    res.status(202).json({ 
      message: 'Simulated incident queued successfully', 
      incidentId: incident.incidentId 
    });
  } catch (error: any) {
    logger.error('Error processing simulation trigger:', error);
    res.status(500).json({ error: 'Failed to trigger simulation', detail: error.message });
  }
});

export default router;
