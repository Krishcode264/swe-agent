import { Incident, IIncident } from '../models/Incident';
import { TimelineEvent } from '../models/TimelineEvent';
import { logger } from '../utils/logger';

export const incidentService = {
  createIncident: async (data: Partial<IIncident>): Promise<IIncident> => {
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
    const event = new TimelineEvent({ incidentId, message, status, type: 'status' });
    await event.save();
    logger.info(`Timeline updated for ${incidentId}: ${message}`);
  },

  addThought: async (incidentId: string, thought: string) => {
    const event = new TimelineEvent({
      incidentId,
      message: thought,
      status: 'thinking',
      type: 'thinking'
    });
    await event.save();
    logger.info(`Agent thought logged for ${incidentId}: ${thought.substring(0, 80)}...`);
  },

  getTimeline: async (incidentId: string) => {
    return await TimelineEvent.find({ incidentId, type: 'status' }).sort({ timestamp: 1 });
  },

  getThoughts: async (incidentId: string) => {
    return await TimelineEvent.find({ incidentId, type: 'thinking' }).sort({ timestamp: 1 });
  }
};
