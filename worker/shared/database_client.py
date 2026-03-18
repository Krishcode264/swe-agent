import requests
import logging
from config import BACKEND_API_URL

logger = logging.getLogger(__name__)

def update_incident_status(incident_id, status, message=None, extra_data=None):
    """
    Updates the incident status and timeline in the backend database.
    """
    try:
        url = f"{BACKEND_API_URL}/incidents/{incident_id}/status"
        payload = {
            "status": status,
            "message": message or f"Status transitioned to {status}",
            "extra_data": extra_data
        }
        response = requests.put(url, json=payload)
        response.raise_for_status()
        logger.info(f"Successfully updated incident {incident_id} to status: {status}")
        return True
    except Exception as e:
        logger.error(f"Failed to update incident status for {incident_id}: {e}")
        return False


def push_thought(incident_id: str, thought: str) -> None:
    """
    Pushes an agent reasoning/thinking entry to the backend.
    This is fire-and-forget — a failure here never blocks the agent workflow.

    Args:
        incident_id: The unique incident identifier.
        thought: A natural language description of what the agent is thinking/doing.
    """
    try:
        url = f"{BACKEND_API_URL}/incidents/{incident_id}/thoughts"
        response = requests.post(url, json={"thought": thought}, timeout=5)
        response.raise_for_status()
        logger.debug(f"Thought logged for {incident_id}: {thought[:60]}...")
    except Exception as e:
        # Never raise — agent thinking logs are non-critical
        logger.warning(f"Could not log agent thought for {incident_id}: {e}")


def sync_incident_data(incident_id, data):
    """
    Syncs generic incident data back to the database.
    """
    try:
        url = f"{BACKEND_API_URL}/incidents/{incident_id}"
        response = requests.put(url, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to sync incident data for {incident_id}: {e}")
        return False
