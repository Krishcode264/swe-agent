import json
import redis
import logging
import requests
from config import REDIS_URL, QUEUE_NAME, BACKEND_API_URL
from shared.database_client import update_incident_status
from agent.agent_runner import process_incident

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Removed local update_incident_status as it is now imported from shared.database_client

def listen_for_tasks():
    logging.info(f"Listening on Redis queue: {QUEUE_NAME}")
    # Blocking pop from the queue
    result = redis_client.blpop(QUEUE_NAME, timeout=0)
    
    if result:
        _, task_data = result
        try:
            incident = json.loads(task_data)
            # The backend puts 'task_id' in the payload, but the worker code sometimes expects 'incidentId'
            incident_id = incident.get("incidentId") or incident.get("task_id")
            
            if not incident_id:
                logging.error(f"Task data missing both incidentId and task_id: {task_data}")
                return

            logging.info(f"Processing new task for incident {incident_id}")
            
            # If the incident payload is minimal (only task_id/repo/status), fetch full details from backend
            if "title" not in incident:
                logging.info(f"Fetching full incident details for {incident_id} from backend API...")
                try:
                    response = requests.get(f"{BACKEND_API_URL}/incidents/{incident_id}")
                    if response.ok:
                        incident = response.json()
                        logging.info(f"Successfully fetched full data for {incident_id}")
                    else:
                        logging.error(f"Failed to fetch incident {incident_id}: {response.status_code}")
                except Exception as fetch_err:
                    logging.error(f"Error fetching incident data: {fetch_err}")

            update_incident_status(incident_id, "running", "Agent worker picking up the task")
            
            # Trigger the agent workflow
            process_incident(incident)
            
        except Exception as e:
            logging.error(f"Failed to process task data: {e}")
