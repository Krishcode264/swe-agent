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
            incident_id = incident.get("task_id") or incident.get("incidentId") or "unknown"
            
            logging.info(f"Processing new task for incident {incident_id}")
            update_incident_status(incident_id, "running", "Agent worker picking up the task")
            
            # Trigger the agent workflow
            process_incident(incident)
            
        except Exception as e:
            logging.error(f"Failed to process task data: {e}")
