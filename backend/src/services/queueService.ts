import { redisClient } from '../config/redis';
import { logger } from '../utils/logger';
import { IIncident } from '../models/Incident';
import { incidentService } from './incidentService';

const QUEUE_NAME = process.env.QUEUE_NAME || 'incident_tasks';

export const queueService = {
  pushTask: async (incident: IIncident) => {
    try {
      const taskPayload = JSON.stringify(incident);
      await redisClient.rPush(QUEUE_NAME, taskPayload);
      logger.info(`Pushed incident ${incident.incidentId} to queue ${QUEUE_NAME}`);
      await incidentService.addTimelineEvent(incident.incidentId, 'Added to queue', 'queued');
    } catch (error) {
      logger.error('Failed to push task to Redis', error);
      throw error;
    }
  }
};
