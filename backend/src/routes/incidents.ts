import { Router, Request, Response } from 'express';
import { incidentService } from '../services/incidentService';
import { logger } from '../utils/logger';

const router = Router();

router.get('/', async (req: Request, res: Response) => {
  try {
    const incidents = await incidentService.getAllIncidents();
    res.json(incidents);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch incidents' });
  }
});

router.get('/:id', async (req: Request, res: Response) => {
  try {
    const incident = await incidentService.getIncidentById(req.params.id);
    if (!incident) return res.status(404).json({ error: 'Not found' });
    res.json(incident);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch incident' });
  }
});

router.get('/:id/timeline', async (req: Request, res: Response) => {
  try {
    const timeline = await incidentService.getTimeline(req.params.id);
    res.json(timeline);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch timeline' });
  }
});

router.get('/:id/thoughts', async (req: Request, res: Response) => {
  try {
    const thoughts = await incidentService.getThoughts(req.params.id);
    res.json(thoughts);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch agent thoughts' });
  }
});

router.post('/:id/thoughts', async (req: Request, res: Response) => {
  try {
    const { thought } = req.body;
    if (!thought) return res.status(400).json({ error: 'thought field is required' });
    await incidentService.addThought(req.params.id, thought);
    res.status(201).json({ message: 'Thought logged' });
  } catch (error) {
    logger.error('Error logging agent thought', error);
    res.status(500).json({ error: 'Failed to log thought' });
  }
});

router.put('/:id', async (req: Request, res: Response) => {
  try {
    const incident = await incidentService.updateIncident(req.params.id, req.body);
    if (!incident) return res.status(404).json({ error: 'Not found' });
    res.json(incident);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update incident' });
  }
});

router.put('/:id/status', async (req: Request, res: Response) => {
  try {
    const { status, message } = req.body;
    const updateMsg = message || `Status changed to ${status}`;
    const incident = await incidentService.updateStatus(req.params.id, status, updateMsg);
    if (!incident) return res.status(404).json({ error: 'Not found' });
    res.json(incident);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update status' });
  }
});

export default router;
