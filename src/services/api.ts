import axios from 'axios';
import { Incident, TimelineEvent } from '../types/incident';

// const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:4000/api';

const API_URL = 'https://swe-agent-1.onrender.com/api';


export const api = {
  getIncidents: async (): Promise<Incident[]> => {
    const response = await axios.get(`${API_URL}/incidents`);
    return response.data;
  },
  
  getIncidentById: async (id: string): Promise<Incident> => {
    const response = await axios.get(`${API_URL}/incidents/${id}`);
    return response.data;
  },
  
  getTimeline: async (id: string): Promise<TimelineEvent[]> => {
    const response = await axios.get(`${API_URL}/incidents/${id}/timeline`);
    return response.data;
  }
};
