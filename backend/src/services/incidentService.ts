import { Incident, IIncident } from '../models/Incident';
import { TimelineEvent } from '../models/TimelineEvent';
import { logger } from '../utils/logger';

export const incidentService = {
  createIncident: async (data: Partial<IIncident>): Promise<IIncident> => {
    // Use upsert so re-triggering the same incidentId doesn't crash with duplicate key error
    const incident = await Incident.findOneAndUpdate(
      { incidentId: data.incidentId },
      { ...data, status: 'queued' },
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );
    await incidentService.addTimelineEvent(incident.incidentId, 'Incident received and created', 'queued');
    return incident;
  },

  getAllIncidents: async () => {
    return await Incident.find().sort({ createdAt: -1 });
  },

  getIncidentById: async (id: string) => {
    return await Incident.findOne({ incidentId: id });
  },

  updateStatus: async (id: string, status: string, message: string) => {
    const incident = await Incident.findOneAndUpdate({ incidentId: id }, { status }, { new: true });
    if (incident) {
      await incidentService.addTimelineEvent(id, message, status);
    }
    return incident;
  },

  updateIncident: async (id: string, data: Partial<IIncident>) => {
    return await Incident.findOneAndUpdate({ incidentId: id }, data, { new: true });
  },

  addTimelineEvent: async (incidentId: string, message: string, status: string) => {
    const event = new TimelineEvent({ incidentId, message, status });
    await event.save();
    logger.info(`Timeline updated for ${incidentId}: ${message}`);
  },

  getTimeline: async (incidentId: string) => {
    return await TimelineEvent.find({ incidentId }).sort({ timestamp: 1 });
  }
};
